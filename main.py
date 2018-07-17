import base64
import csv
import json
import multiprocessing
import random
import io
from io import BytesIO

import math
import mercantile
import urllib.request
import PIL.Image
import cairo


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


def get_image(west, south, east, north, zoom):
    """
    return glued tiles as PIL image
    :param west: west longitude in degrees
    :param south: south latitude in degrees
    :param east: east longitude in degrees
    :param north: north latitude in degrees
    :param zoom: wanted size
    :return: Image
    """
    tiles = list(mercantile.tiles(west, south, east, north, zoom))

    tile_size = 256
    min_x = min_y = max_x = max_y = None

    for tile in tiles:
        min_x = min(min_x, tile.x) if min_x is not None else tile.x
        min_y = min(min_y, tile.y) if min_y is not None else tile.y
        max_x = max(max_x, tile.x) if max_x is not None else tile.x
        max_y = max(max_y, tile.y) if max_y is not None else tile.y

    out_img = PIL.Image.new(
        'RGB',
        ((max_x - min_x + 1) * tile_size, (max_y - min_y + 1) * tile_size)
    )

    pool = multiprocessing.Pool(8)
    results = pool.map(_download_tile, tiles)

    for img, tile in results:
        left = tile.x - min_x
        top = tile.y - min_y
        bounds = (left * tile_size, top * tile_size, (left + 1) * tile_size, (top + 1) * tile_size)
        out_img.paste(img, bounds)

    return out_img, tiles


if __name__ == '__main__':
    points = []
    with open('irkutsk_kyahta.json') as f:
        out = json.load(f)
        for p in out:
            points.append({
                'lat': p[1],
                'lng': p[0],
            })

    # points = points[:1000]

    min_lat = min([i['lat'] for i in points])
    min_lng = min([i['lng'] for i in points])
    max_lat = max([i['lat'] for i in points])
    max_lng = max([i['lng'] for i in points])

    image, tiles = get_image(west=min_lng, south=min_lat, east=max_lng, north=max_lat, zoom=9)

    tiles_bounding = list(mercantile.xy_bounds(t) for t in tiles)
    min_mercator_lng = min(t.left for t in tiles_bounding)
    max_mercator_lng = max(t.right for t in tiles_bounding)
    min_mercator_lat = min(t.bottom for t in tiles_bounding)
    max_mercator_lat = max(t.top for t in tiles_bounding)
    delta_mercator_lat = max_mercator_lat - min_mercator_lat
    delta_mercator_lng = max_mercator_lng - min_mercator_lng

    kx = image.size[0] / (max_mercator_lng - min_mercator_lng)
    ky = image.size[1] / (max_mercator_lat - min_mercator_lat)

    def get_xy(point):
        x, y = mercantile.xy(point['lng'], point['lat'])
        x = (x - min_mercator_lng) * kx
        y = image.size[1] - (y - min_mercator_lat) * ky
        return x, y

    image_data = BytesIO()
    image.save(image_data, format='png')
    image_data.seek(0)
    with cairo.ImageSurface.create_from_png(image_data) as surface:
        context = cairo.Context(surface)
        context.set_line_width(15)
        context.set_source_rgba(255, 0, 0, 0.5)
        for index, p in enumerate(points):
            x, y = get_xy(p)
            if index == 0:
                context.move_to(x, y)
            else:
                context.line_to(x, y)
        context.stroke()

        context.set_source_rgba(255, 0, 0, 0.85)
        x, y = get_xy(points[0])
        context.arc(x, y, 13, 0, 2 * math.pi)
        context.fill()

        context.set_source_rgba(255, 0, 0, 0.85)
        x, y = get_xy(points[-1])
        context.arc(x, y, 13, 0, 2 * math.pi)
        context.fill()

        surface.write_to_png("irkutsk_kyahta.png")
