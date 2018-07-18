geo2image
=========

The package which allows to create static images using openstreetmap, add ways and markers.

Install
=======

```
pip install git+https://github.com/SevenLines/geo2image/
```

Usage
=====

Download image
--------------

```
import geo2image

# initialize geoimage instance, by providing bounds
geo_image = geo2image.GeoImage(west=102.95, south=51.2, east=110.7, north=56.06, default_zoom=8)
# download image from openstreetmap
geo_image.update()
# save image to file
geo_image.image.save("baikal.png")

# change image zoom
geo_image.zoom = 5
# invalidate image
geo_image.update()
# save to file
geo_image.image.save("baikal_zoom_5.png")
```

Draw on image
-------------

We draw using pycairo as it has much more capabilities then Pillow ImageDraw instance

```
import geo2image
import cairo
import mercantile
import math

if __name__ == '__main__':
    geo_image = geo2image.GeoImage(west=102.95, south=51.2, east=110.7, north=56.06)
    geo_image.update()

    # create cairo draw surface
    with geo_image.cairo_surface() as surface:
        # get surface context
        context = cairo.Context(surface)
        # pass transformation matrix
        with geo_image.cairo_matrix_override(context):
            context.set_source_rgba(255, 0, 0, 0.5)
            x, y = mercantile.xy(104.306, 52.283) # convert Irkutsk city coordinate to mercator

            # draw circle, we have to divide by geo_image.kx,
            # cause due to matrix override context, we use metrics system
            context.arc(x, y, 20 / geo_image.kx, 0, 2 * math.pi)
            context.fill()
        surface.write_to_png("baikal.png")
```