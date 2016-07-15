#!/usr/bin/python3

#   Copyright (C) 2016  Axel Wegener <a.wegener@ifaoe.de>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
from argparse import ArgumentParser
import os
import subprocess
import tempfile
# from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# function to assemble gdal control points in the right format
def get_gcp(pixel_x, pixel_y, utm_x, utm_y):
    return '-gcp {0} {1} {2} {3}'.format(pixel_x, pixel_y, utm_x, utm_y)


# main encapsulated funtion in order to use it in library mode
def process(input_file, output_file, north_east, north_west, south_east, south_west, threads, resolution, compress, quality, resample, utm, block_size, verbose,
            opencl, overwrite):
    if verbose:
        logger.setLevel(logging.DEBUG)

    logger.debug('Checking file locations...')

    if not os.path.isfile(input_file):
        logger.critical('Input file {0} does not exist.'.format(input_file))
        exit(1)

    if os.path.exists(output_file):
        if overwrite:
            print('Image {0} already exists. Overwriting as per option.'.format(output_file))
            os.remove(output_file)
        else:
            logger.critical('Output file {0} already exists.'.format(output_file))
            exit(1)

    if not os.path.exists(os.path.dirname(output_file)):
        logger.debug('Outpath {0} does not exist. Creating.'.format(os.path.dirname(output_file)))
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # pillow does not support 16bit images
    # instead get the image size from bash
    #
    # print('Getting input image file {0}...'.format(input_file))
    # input_image = Image.open(input_file)
    # if not input_image.veryify():
    #     logger.critical('{0} is not a valid image.'.format(input_file))
    #     exit(1)
    #
    # width, height = input_image.size

    width, height = subprocess.run('gdalinfo {0} | grep "Size is" | sed -e "s/[^0-9,]*//g"'.format(input_file),
                                   shell=True, stdout=subprocess.PIPE).stdout.decode('utf-8').replace('\n', '').split(',')

    logger.debug('Image size is {0} {1}'.format(width, height))

    # assemble gdal options
    # use all cpus if no other option is set
    if threads == 0:
        thread_count = 'ALL_CPUS'
    else:
        thread_count = threads

    translation_options = ' -oo NUM_THREADS={0} -r {1}'.format(thread_count, resample)
    translation_epsg = '-a_srs epsg:{0}'.format(utm)

    # get gdal control points
    nw_gcp = get_gcp(0, 0, north_west[0], north_west[1])
    sw_gcp = get_gcp(0, height, south_west[0], south_west[1])
    ne_gcp = get_gcp(width, 0, north_east[0], north_east[1])
    se_gcp = get_gcp(width, height, south_east[0], south_east[1])

    # check gdal version in order to take advantage of advanced multicore options
    gdal_version = int(subprocess.run('gdal-config --version', shell=True, stdout=subprocess.PIPE).stdout.decode('utf8').replace('.', '')[0:3])
    logger.debug('GDAL version is {0}'.format(gdal_version))

    warp_parallel = ''
    translate_parallel = ''
    if gdal_version >= 210:
        warp_parallel = '-doo NUM_THREADS={0}'.format(thread_count)
        if not opencl:
            logger.debug("OpenCL disabled.")
            warp_parallel += ' -wo "USE_OPENCL=FALSE"'
        translate_parallel = '-co NUM_THREADS={0}'.format(thread_count)
    else:
        logger.debug('GDAL version < 2.1.0. Using single threaded functions.')

    # create translate temporary file
    translate_file = tempfile.NamedTemporaryFile()
    translate_name = translate_file.name

    # assemble gdal_translate bash command
    translate_run = ' '.join(
        ['gdal_translate', '-of GTiff', nw_gcp, sw_gcp, ne_gcp, se_gcp, translation_epsg, translation_options, translate_parallel, input_file, translate_name])
    print('Transforming image to given coordinates...')
    logger.debug(translate_run)
    subprocess.run(translate_run, shell=True, check=True)

    # define more warp options
    warp_options = '--config GDAL_CACHEMAX 8000 -wm 8000 -wo NUM_THREADS={0} -oo NUM_THREADS={0} -r {1}'.format(thread_count, resample)
    warp_resolution = '-tr {0} {0}'.format(resolution, resolution)
    warp_blocksize = '-co BLOCKXSIZE={0} -co BLOCKYSIZE={1}'.format(block_size[0], block_size[1])
    warp_epsg = '-t_srs epsg:{0}'.format(utm)

    # if we want to compress the final image we need another translate step, hence another temporary file
    # else just write the final file
    if compress:
        warp_file = tempfile.NamedTemporaryFile()
        warp_name = warp_file.name
    else:
        warp_name = output_file

    # assemble gdalwarp bash command
    warp_run = ' '.join(
        ['gdalwarp', '-of GTiff', '-dstnodata \'0 0 0\'', warp_epsg, warp_options, warp_blocksize, warp_resolution, warp_parallel, translate_name, warp_name])
    print('Warping image...')
    logger.debug(warp_run)
    subprocess.run(warp_run, shell=True, check=True)

    # another gdal_translate in order to compress the final image
    if compress:
        compress_run = ' '.join(['gdal_translate', '-of GTiff', '-ot Byte', '-scale 0 65535 0 255', '-co COMPRESS=JPEG',
                                 '-co JPEG_QUALITY={0}'.format(quality), warp_name, output_file])
        print('Compressing image...')
        logger.debug(compress_run)
        subprocess.run(compress_run, shell=True, check=True)

    aux_file = output_file + '.aux.xml'
    if os.path.isfile(aux_file):
        logger.debug('Removing auxillary file: {0}'.format(aux_file))
        os.remove(aux_file)
    exit(1)


if __name__ == '__main__':
    parser = ArgumentParser(description='Georeference DAISI images from tif')

    parser.add_argument('-v', '--verbose', action='store_true', help='Verbosity')
    parser.add_argument('-r', '--resolution', type=float, default=0.02, help='Target resolution in meters (default: 0.02)')
    parser.add_argument('-c', '--compress', action='store_true', help='Enable JPEG compression')
    parser.add_argument('-q', '--quality', type=int, default=95, help='Compression quality, only for jpg (default: 95)')
    parser.add_argument('-o', '--overwrite', action='store_true', help='Overwrite existing images')
    parser.add_argument('--block-size', type=int, nargs=2, default=[256, 256], help='X and Y Blocksize for tiff type (default: 256 256')
    parser.add_argument('--resample', type=str, default='lanczos', help='Resampling algorithm (default: lanczos)')
    parser.add_argument('--utm', type=int, default=32632, help='UTM Sector (default: 32632)')
    parser.add_argument('-t', '--threads', type=int, default=0, help='Number of threads to use (default: all)')
    parser.add_argument('input', type=str, help='Input path of unreferenced tiff')
    parser.add_argument('output', type=str, help='Output path for georeferenced image')
    parser.add_argument('north_west', type=float, nargs=2, help='North west corner')
    parser.add_argument('north_east', type=float, nargs=2, help='North east corner')
    parser.add_argument('south_west', type=float, nargs=2, help='South west corner')
    parser.add_argument('south_east', type=float, nargs=2, help='South east corner')
    parser.add_argument('--opencl', action='store_true', help='Enable OpenCl.')

    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)

    process(input_path, output_path, args.north_east, args.north_west, args.south_east, args.south_west, args.threads, args.resolution, args.compress,
            args.quality, args.resample, args.utm, args.block_size, args.verbose, args.opencl, args.overwrite)

    exit(0)
