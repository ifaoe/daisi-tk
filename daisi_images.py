#!/usr/bin/python3

import logging
import psycopg2
from argparse import ArgumentParser
from gdal_tif2geo import process
import multiprocessing
import subprocess
from joblib import Parallel, delayed
from math import ceil
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parallel_process(linco_path, linco_args, threads, row, overwrite, temppath):
    [epsg, iiq_file, geo_file, ne_x, ne_y, nw_x, nw_y, sw_x, sw_y, se_x, se_y] = row
    print("Processing {0} -> {1}".format(iiq_file, geo_file))
    # convert iiq -> tiff
    # create temporary file
    temp_file = tempfile.NamedTemporaryFile()
    # run linco
    linco_command = ('nice', '-n 19', linco_path, iiq_file, temp_file.name, '-cputhreads={threads}'.format(threads=threads), linco_args)
    logger.debug(' '.join(linco_command))
    subprocess.run(linco_command)

    # create geotiff
    process(temp_file.name, geo_file, [ne_x, ne_y], [nw_x, nw_y], [se_x, se_y], [sw_x, sw_y], threads,
            0.02, True, 95, 'lanczos', epsg, [256, 256], args.verbose, False, overwrite, temppath)

if __name__ == '__main__':
    parser = ArgumentParser(description='Georeference DAISI images from tif.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbosity.')
    parser.add_argument('-s', '--session', type=str, default='.*', help='Session pattern (default: .*).')
    parser.add_argument('-t', '--transect', type=str, default='.*', help='Transect pattern (default: .*).')
    parser.add_argument('-c', '--camera', type=str, default='.*', help='Camera pattern (default: .*).')
    parser.add_argument('-i', '--image', type=str, default='.*', help='Image pattern (default: .*).')
    parser.add_argument('-H', '--host', type=str, default='127.0.0.1', help='Database host (default: 127.0.0.1).')
    parser.add_argument('-d', '--database', type=str, default='daisi', help='Database name (default: DAISI).')
    parser.add_argument('-u', '--user', type=str, default='daisi', help='Database user (default: DAISI).')
    parser.add_argument('-P', '--password', type=str, default='18ifaoe184', help='Database password.')
    parser.add_argument('-p', '--port', type=str, default='5432', help='Database port (default: 5432).')
    parser.add_argument('-l', '--location', type=str, default='rostock', help='Image data location (default: rostock)')
    parser.add_argument('-o', '--overwrite', action='store_true', help='Overwrite image if it already exists.')
    parser.add_argument('--linco-path', type=str, default='/usr/local/bin/linco', help='Location of linco executable.')
    parser.add_argument('--linco-args', type=str, default='-bits=16 -shadowRecovery=75 -highlightRecovery=75',
                        help='Set linco arguments (default: -bits=16 -shadowRecovery=75 -highlightRecovery=75).')
    parser.add_argument('--linco-help', action='store_true', help='Get linco help (overwrites all other arguments).')
    parser.add_argument('--temp-path', type=str, help='Path for temporary files')

    args = parser.parse_args()

    if args.linco_help:
        subprocess.run([args.linco_path, '--help'])
        exit(1)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # connecting to database
    connection = psycopg2.connect(database=args.database, host=args.host, port=args.port, user=args.user, password=args.password)
    cursor = connection.cursor()

    cursor.execute("SELECT epsg, iiq_path, geo_path, ne_x, ne_y, nw_x, nw_y, sw_x, sw_y, se_x, se_y FROM daisi_dev.gdal_images "
                   "WHERE location=%s AND session~%s AND transect~%s AND camera~%s AND image~%s",
                   (args.location, args.session, args.transect, args.camera, args.image))
    rows = cursor.fetchall()
    row_count = len(rows)
    if row_count == 0:
        logger.critical('No images match the query {0}'.format(cursor.query))
        exit(1)
    logger.debug('{0} images match the query {1}'.format(row_count, cursor.query))
    connection.commit()

    cpu_count = multiprocessing.cpu_count()

    thread_count = min(cpu_count, ceil(cpu_count/row_count))
    process_count = min(cpu_count, ceil(cpu_count/thread_count))

    logger.debug('Found {0} CPUs. Using {1} processes with {2} thread(s) each.'.format(cpu_count, process_count, thread_count))

    Parallel(n_jobs=process_count)(delayed(parallel_process)(args.linco_path, thread_count, row, args.overwrite, args.temp_path) for row in rows)

