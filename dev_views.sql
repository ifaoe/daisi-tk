DROP VIEW daisi_dev.gdal_images;
CREATE OR REPLACE VIEW daisi_dev.gdal_images AS
SELECT
    p.location,
    32600 + p.utm_sector as epsg,
    i.session::text,
    i.transect::text,
    i.camera::text,
    i.image::text,
    concat(path, 'cam', i.camera, '/geo/', i.image, '.tif') geo_path,
    concat(iiq_path, 'cam', i.camera, '/iiq/', i.image, '.IIQ') iiq_path,
    ST_X(ST_TRANSFORM(north_west_corner, 32600+p.utm_sector)) nw_x, ST_Y(ST_TRANSFORM(north_west_corner, 32600+p.utm_sector)) nw_y,
    ST_X(ST_TRANSFORM(north_east_corner, 32600+p.utm_sector)) ne_x, ST_Y(ST_TRANSFORM(north_east_corner, 32600+p.utm_sector)) ne_y,
    ST_X(ST_TRANSFORM(south_west_corner, 32600+p.utm_sector)) sw_x, ST_Y(ST_TRANSFORM(south_west_corner, 32600+p.utm_sector)) sw_y,
    ST_X(ST_TRANSFORM(south_east_corner, 32600+p.utm_sector)) se_x, ST_Y(ST_TRANSFORM(south_east_corner, 32600+p.utm_sector)) se_y
FROM
    images i
JOIN
    projects p ON i.session=p.flight_id
WHERE
    p.project_id=p.flight_id;