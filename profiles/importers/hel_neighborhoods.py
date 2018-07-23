import os
import re
import yaml
from datetime import datetime
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.gis.geos import MultiPolygon

from munigeo import ocd
from munigeo.importer.helsinki import GK25_SRID, HelsinkiImporter, poly_diff, PROJECTION_SRID
from munigeo.models import AdministrativeDivision, AdministrativeDivisionGeometry, Municipality


class HelsinkiNeighborhoodsImporter(HelsinkiImporter):
    """
    This importer copies most of the functionality from its parent, except for:
    1. Custom config file, where neighborhoods are parents of sub_districts
    2. More inclusive logic for finding the parent neighborhood (see lines 76-84)
    """

    def import_neighborhoods(self):
        importers_dir = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(importers_dir, 'configs/hel_neighborhoods.yml')
        config = yaml.safe_load(open(path, 'r'))
        self.division_data_path = os.path.join(self.muni_data_path, config['paths']['neighborhood'])

        muni = Municipality.objects.get(division__origin_id=config['origin_id'])
        self.muni = muni
        for div in config['neighborhoods']:
            self._import_one_division_type(muni, div)

    def _import_division(self, muni, div, type_obj, syncher, parent_dict, feat):
        #
        # Geometry
        #
        geom = feat.geom
        if not geom.srid:
            geom.srid = GK25_SRID
        if geom.srid != PROJECTION_SRID:
            ct = CoordTransform(SpatialReference(geom.srid), SpatialReference(PROJECTION_SRID))
            geom.transform(ct)
        # geom = geom.geos.intersection(parent.geometry.boundary)
        geom = geom.geos
        if geom.geom_type == 'Polygon':
            geom = MultiPolygon(geom, srid=geom.srid)

        #
        # Attributes
        #
        attr_dict = {}
        lang_dict = {}
        for attr, field in div['fields'].items():
            if isinstance(field, dict):
                # Languages
                d = {}
                for lang, field_name in field.items():
                    val = feat[field_name].as_string()
                    # If the name is in all caps, fix capitalization.
                    if not re.search('[a-z]', val):
                        val = val.title()
                    d[lang] = val.strip()
                lang_dict[attr] = d
            else:
                val = feat[field].as_string()
                attr_dict[attr] = val.strip()
        origin_id = attr_dict['origin_id']
        del attr_dict['origin_id']

        if 'parent' in div:
            if 'parent_id' in attr_dict:
                parent = parent_dict[attr_dict['parent_id']]
                del attr_dict['parent_id']
            else:
                # If no parent id is available, we determine the parent
                # heuristically by choosing the one that we overlap with
                # the most.
                most_suitable_parent = None
                for parent in parent_dict.values():
                    diff_area = int(poly_diff(geom, parent.geometry.boundary))
                    if not most_suitable_parent or most_suitable_parent[1] > diff_area:
                        most_suitable_parent = (parent, diff_area)

                if not most_suitable_parent:
                    raise Exception("No parent found for %s" % origin_id)
                parent = most_suitable_parent[0]
        elif 'parent_ocd_id' in div:
            try:
                parent = AdministrativeDivision.objects.get(ocd_id=div['parent_ocd_id'])
            except AdministrativeDivision.DoesNotExist:
                parent = None
        else:
            parent = muni.division

        if 'parent' in div and parent:
            full_id = "%s-%s" % (parent.origin_id, origin_id)
        else:
            full_id = origin_id
        obj = syncher.get(full_id)
        if not obj:
            obj = AdministrativeDivision(origin_id=origin_id, type=type_obj)

        validity_time_period = div.get('validity')
        if validity_time_period:
            obj.start = validity_time_period.get('start')
            obj.end = validity_time_period.get('end')
            if obj.start:
                obj.start = datetime.strptime(obj.start, '%Y-%m-%d').date()
            if obj.end:
                obj.end = datetime.strptime(obj.end, '%Y-%m-%d').date()

        if div.get('no_parent_division', False):
            muni = None

        obj.parent = parent
        obj.municipality = muni

        for attr in attr_dict.keys():
            setattr(obj, attr, attr_dict[attr])
        for attr in lang_dict.keys():
            for lang, val in lang_dict[attr].items():
                obj.set_current_language(lang)
                setattr(obj, attr, val)

        if 'ocd_id' in div:
            assert (parent and parent.ocd_id) or 'parent_ocd_id' in div
            if parent:
                if div.get('parent_in_ocd_id', False):
                    args = {'parent': parent.ocd_id}
                else:
                    args = {'parent': muni.division.ocd_id}
            else:
                args = {'parent': div['parent_ocd_id']}
            val = attr_dict['ocd_id']
            args[div['ocd_id']] = val
            obj.ocd_id = ocd.make_id(**args)
            self.logger.debug("%s" % obj.ocd_id)
        obj.save()
        syncher.mark(obj)

        try:
            geom_obj = obj.geometry
        except AdministrativeDivisionGeometry.DoesNotExist:
            geom_obj = AdministrativeDivisionGeometry(division=obj)

        geom_obj.boundary = geom
        geom_obj.save()
