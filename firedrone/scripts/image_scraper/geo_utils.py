#!/usr/bin/env python3
############################################################################ File: utils.py
# Date: 03/13/2023
# Description: Util functions used to geo-tag jpegs
# Version: 1.0 - Baseline
# Version: 1.1 - Remove boolean parameter from set_gps_loc (03/18/2023)
###########################################################################
import pyexiv2
import fractions
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime

def to_degree(value, loc):
    if value < 0:
        loc_value = loc[0]
    elif value > 0:
        loc_value = loc[1]
    else:
        loc_value = ""
    absolute_value = abs(value)
    deg =  int(absolute_value)
    t1 = (absolute_value-deg)*60
    min = int(t1)
    sec = round((t1 - min)* 60, 5)
    return (deg, min, sec, loc_value)


def str_by_recursion(t, s=''):
    if not t: return ''

    return str(t[0]) + str_by_recursion(t[1:])

def set_gps_loc(file_name, lat, lng, alt, utc_time):
    """
        Adding GPS tag
    """
    lat_deg = to_degree(lat, ["S", "N"])
    lng_deg = to_degree(lng, ["W", "E"])

    exiv_lat = (fractions.Fraction(lat_deg[0] , 1), \
            fractions.Fraction(int(lat_deg[1]), 1), \
            fractions.Fraction(int(lat_deg[2] * 60000), 60000))
    exiv_lng = (fractions.Fraction(lng_deg[0], 1), \
            fractions.Fraction(int(lng_deg[1]), 1), \
            fractions.Fraction(int(lng_deg[2] * 60000), 60000))

    tel_time = datetime.utcfromtimestamp(int(utc_time/1000000))

    exiv_image = pyexiv2.ImageMetadata(file_name)
    exiv_image.read()

    exiv_image["Exif.Image.DateTime"] = tel_time
    exiv_image["Exif.Image.DateTimeOriginal"] = tel_time
    exiv_image["Exif.GPSInfo.GPSLatitude"] = exiv_lat
    exiv_image["Exif.GPSInfo.GPSLatitudeRef"] = lat_deg[3]
    exiv_image["Exif.GPSInfo.GPSLongitude"] = exiv_lng
    exiv_image["Exif.GPSInfo.GPSLongitudeRef"] = lng_deg[3]
    exiv_image["Exif.GPSInfo.GPSAltitudeRef"] = '0' if alt >= 0 else '1'
    exiv_image["Exif.GPSInfo.GPSAltitude"] = fractions.Fraction(alt)
    exiv_image["Exif.Image.GPSTag"] = 654
    exiv_image["Exif.GPSInfo.GPSMapDatum"] = "WGS-84"
    exiv_image["Exif.GPSInfo.GPSVersionID"] = '2 3 0 0'
    exiv_image["Exif.GPSInfo.GPSTimeStamp"] = fractions.Fraction(tel_time.hour,1), fractions.Fraction(tel_time.minute,1), fractions.Fraction(tel_time.second,1)
    exiv_image.write(True)


