#!/usr/bin/python3

import logging
import psycopg2
from argparse import ArgumentParser
from gdal_tif2geo import process

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    parser = ArgumentParser(description='Georeference DAISI images from tif.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbosity.')
    parser.add_argument('-s', '--session', type=str, default='%', help='Session pattern (default: %).')
    parser.add_argument('-t', '--transect', type=str, default='%', help='Transect pattern (default: %).')
    parser.add_argument('-c', '--camera', type=str, default='%', help='Camera pattern (default: %).')
    parser.add_argument('-i', '--image', type=str, default='%', help='Image pattern (default: %).')
    parser.add_argument('-H', '--host', type=str, default='127.0.0.1', help='Database host (default: 127.0.0.1).')
    parser.add_argument('-d', '--database', type=str, default='daisi', help='Database name (default: DAISI).')
    parser.add_argument('-u', '--user', type=str, default='daisi', help='Database user (default: DAISI).')
    parser.add_argument('-P', '--password', type=str, default='18ifaoe184', help='Database password.')
    parser.add_argument('-p', '--port', type=str, default='5432', help='Database port (default: 5432).')
    parser.add_argument('-l', '--location', type=str, default='rostock', help='Image data location (default: rostock)')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # connecting to database
    connection = psycopg2.connect(database=args.database, host=args.host, port=args.port, user=args.user, password=args.password)
    cursor = connection.cursor()

    cursor.execute("SELECT epsg, iiq_path, geo_path FROM daisi_dev.gdal_images WHERE session~%s AND transect~%s AND camera~%s AND image~%s")

