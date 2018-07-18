import base64
import csv
import json
import multiprocessing
import random
import io
from contextlib import contextmanager
from io import BytesIO

import math
import mercantile
import urllib.request
import cairo
import PIL.Image
from cairo._cairo import Context


class GeoImageImageIsNotInitialized(Exception):
    pass


class GeoImage(object):
    TILE_SIZE = 256

    def __init__(self, west, south, east, north, default_zoom=8, pool_workers=16):
        self._west = west
        self._south = south
        self._east = east
        self._north = north
        self._zoom = default_zoom
        self._image = None
        self.pool_workers = pool_workers

    @staticmethod
    def _download_tile(tile: mercantile.Tile):
        """
        Helper function for downloading associated image
        """
        server = random.choice(['a', 'b', 'c'])
        url = 'http://{server}.tile.openstreetmap.org/{zoom}/{x}/{y}.png'.format(
            server=server,
            zoom=tile.z,
            x=tile.x,
            y=tile.y
        )
        response = urllib.request.urlopen(url)
        img = PIL.Image.open(io.BytesIO(response.read()))

        return img, tile

    def _download_image(self):
        """
        return glued tiles as PIL image
        :param west: west longitude in degrees
        :param south: south latitude in degrees
        :param east: east longitude in degrees
        :param north: north latitude in degrees
        :param zoom: wanted size
        :return: Image
        """
        tiles = list(mercantile.tiles(self._west, self._south, self._east, self._north, self._zoom))

        min_x = min_y = max_x = max_y = None

        for tile in tiles:
            min_x = min(min_x, tile.x) if min_x is not None else tile.x
            min_y = min(min_y, tile.y) if min_y is not None else tile.y
            max_x = max(max_x, tile.x) if max_x is not None else tile.x
            max_y = max(max_y, tile.y) if max_y is not None else tile.y

        out_img = PIL.Image.new(
            'RGB',
            ((max_x - min_x + 1) * self.TILE_SIZE, (max_y - min_y + 1) * self.TILE_SIZE)
        )

        pool = multiprocessing.Pool(self.pool_workers)
        results = pool.map(self._download_tile, tiles)

        for img, tile in results:
            left = tile.x - min_x
            top = tile.y - min_y
            bounds = (left * self.TILE_SIZE, top * self.TILE_SIZE, (left + 1) * self.TILE_SIZE, (top + 1) * self.TILE_SIZE)
            out_img.paste(img, bounds)

        tiles_bounding = list(mercantile.xy_bounds(t) for t in tiles)
        min_mercator_lng = min(t.left for t in tiles_bounding)
        max_mercator_lng = max(t.right for t in tiles_bounding)
        min_mercator_lat = min(t.bottom for t in tiles_bounding)
        max_mercator_lat = max(t.top for t in tiles_bounding)

        kx = out_img.size[0] / (max_mercator_lng - min_mercator_lng)
        ky = out_img.size[1] / (max_mercator_lat - min_mercator_lat)

        self._image = out_img
        self._left = min_mercator_lng
        self._right = max_mercator_lng
        self._top = max_mercator_lat
        self._bottom = min_mercator_lat
        self._kx = kx
        self._ky = ky

    @property
    def image(self):
        if not self._image:
            raise GeoImageImageIsNotInitialized
        return self._image

    @property
    def left(self):
        if not self._image:
            raise GeoImageImageIsNotInitialized
        return self._left

    @property
    def right(self):
        if not self._image:
            raise GeoImageImageIsNotInitialized
        return self._right

    @property
    def top(self):
        if not self._image:
            raise GeoImageImageIsNotInitialized
        return self._top

    @property
    def bottom(self):
        if not self._image:
            raise GeoImageImageIsNotInitialized
        return self._bottom

    @property
    def kx(self):
        if not self._image:
            raise GeoImageImageIsNotInitialized
        return self._kx

    @property
    def ky(self):
        if not self._image:
            raise GeoImageImageIsNotInitialized
        return self._ky

    @contextmanager
    def cairo_matrix_override(self, context: Context):
        matrix = context.get_matrix()
        context.translate(0, self.image.size[1])
        context.scale(self.kx, -self.ky)
        context.translate(-self.left, -self.bottom)
        yield context
        context.set_matrix(matrix)

    @contextmanager
    def cairo_surface(self):
        image_data = BytesIO()
        self.image.save(image_data, format='png')
        image_data.seek(0)

        with cairo.ImageSurface.create_from_png(image_data) as surface:
            yield surface

    def update(self):
        self._download_image()


if __name__ == '__main__':
    points = []
    with open('irkutsk_kyahta.json') as f:
        out = json.load(f)
        for p in out:
            points.append({
                'lat': p[1],
                'lng': p[0],
            })

    min_lat = min([i['lat'] for i in points])
    min_lng = min([i['lng'] for i in points])
    max_lat = max([i['lat'] for i in points])
    max_lng = max([i['lng'] for i in points])

    geo_image = GeoImage(west=min_lng, south=min_lat, east=max_lng, north=max_lat)
    geo_image.update()

    with geo_image.cairo_surface() as surface:
        context = cairo.Context(surface)

        with geo_image.cairo_matrix_override(context):
            context.set_line_width(15 / geo_image.kx)
            context.set_source_rgba(255, 0, 0, 0.5)
            for index, p in enumerate(points):
                x, y = mercantile.xy(p['lng'], p['lat'])
                if index == 0:
                    context.move_to(x, y)
                else:
                    context.line_to(x, y)
            context.stroke()

            for p in [points[0], points[1]]:
                context.set_source_rgba(255, 0, 0, 0.5)
                x, y = mercantile.xy(p['lng'], p['lat'])
                context.arc(x, y, 20 / geo_image.kx, 0, 2 * math.pi)
                context.fill()

            surface.write_to_png("irkutsk_kyahta.png")
