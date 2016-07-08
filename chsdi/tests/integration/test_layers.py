# -*- coding: utf-8 -*-

import os
from webtest import TestApp
from pyramid.paster import get_app
from sqlalchemy import distinct
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import func

from chsdi.models.bod import LayersConfig
from chsdi.models import models_from_bodid
from chsdi.models.grid import get_grid_spec


class LayersChecker(object):

    def __enter__(self):
        def num(s):
            if s.isdigit():
                return long(s)
            else:
                return s

        self.testapp = TestApp(get_app('development.ini'))
        self.session = scoped_session(sessionmaker())

        # configuration via environment. Default is None for all
        self.staging = os.environ.get('CHSDI_STAGING') if os.environ.get('CHSDI_STAGING') is not None else 'prod'
        self.onlylayer = os.environ.get('CHSDI_ONLY_LAYER')
        self.randomFeatures = os.environ.get('CHSDI_RANDOM_FEATURES') == 'True'
        self.nrOfFeatures = num(os.environ.get('CHSDI_NUM_FEATURES')) if os.environ.get('CHSDI_NUM_FEATURES') is not None else 1
        self.emptyGeoTables = self.testapp.app.registry.settings.get('empty_geotables').split(',')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.session.close()
        del self.testapp
        return False

    def ilayers(self, tooltip=None, hasLegend=None, searchable=None, geojson=None):
        valNone = None
        query = self.session.query(distinct(LayersConfig.layerBodId)) \
            .filter(LayersConfig.staging == self.staging) \
            .filter(LayersConfig.parentLayerId == valNone) \
            .filter(LayersConfig.srid != '4326')
        if tooltip is not None:
            query = query.filter(LayersConfig.tooltip == tooltip)
        if hasLegend is not None:
            query = query.filter(LayersConfig.hasLegend == hasLegend)
        if searchable is not None:
            query = query.filter(LayersConfig.searchable == searchable)
        if geojson is not None:
            if geojson:
                query = query.filter(LayersConfig.type == 'geojson')
            else:
                query = query.filter(LayersConfig.type != 'geojson')
        for q in query:
            if self.onlylayer is None or q[0] == self.onlylayer:
                yield q[0]

    def ilayersAllModels(self):
        for layer in self.ilayers(tooltip=True, geojson=False):
            gridSpec = get_grid_spec(layer)
            if gridSpec is None and layer not in self.emptyGeoTables:
                models = models_from_bodid(layer)
                assert (models is not None and len(models) > 0), layer
                for model in models:
                    primaryKeyColumn = model.primary_key_column()
                    query = self.session.query(primaryKeyColumn)
                    query = query.limit(1)
                    try:
                        featureId = query.one()[0]
                    except NoResultFound:
                        featureId = None
                    yield layer, featureId, model, primaryKeyColumn

    def ilayersWithFeatures(self):
        for layer in self.ilayers(tooltip=True, geojson=False):
            gridSpec = get_grid_spec(layer)
            if gridSpec is None and layer not in self.emptyGeoTables:
                models = models_from_bodid(layer)
                assert (models is not None and len(models) > 0), layer
                model = models[0]
                query = self.session.query(model.primary_key_column())
                # Depending on db size, random row is slow
                if self.randomFeatures:
                    query = query.order_by(func.random())
                if isinstance(self.nrOfFeatures, (int, long)):
                    query = query.limit(self.nrOfFeatures)
                hasExtended = model.__extended_info__ if hasattr(model, '__extended_info__') else False
                for q in query:
                    yield (layer, str(q[0]), hasExtended)

    def checkHtmlPopup(self, layer, feature, extended):
        for lang in ('de', 'fr', 'it', 'rm', 'en'):
            link = '/rest/services/all/MapServer/' + layer + '/' + feature + '/htmlPopup?callback=cb&lang=' + lang
            resp = self.testapp.get(link)
            assert resp.status_int == 200, link
            if extended:
                link = link.replace('htmlPopup', 'extendedHtmlPopup')
                resp = self.testapp.get(link)
                assert resp.status_int == 200, link

    def checkLegend(self, layer):
        for lang in ('de', 'fr', 'it', 'rm', 'en'):
            link = '/rest/services/all/MapServer/' + layer + '/legend?callback=cb&lang=' + lang
            resp = self.testapp.get(link)
            assert resp.status_int == 200, link

    def checkLegendImage(self, layer, legendImages):
        for lang in ('de', 'fr', 'it', 'rm', 'en'):
            assert ((layer + '_' + lang) in legendImages), layer + '_' + lang

    def checkSearch(self, layer):
        models = models_from_bodid(layer)
        assert (models is not None and len(models) > 0), layer
        model = models[0]
        expectedStatus = 200
        # Special treatment for non-distributed sphinx indices (single model)
        if len(models) == 1:
            query = self.session.query(model.primary_key_column())
            # we expect 404 errors for searchable layers without any data (no sphinx index)
            if query.first() is None:
                expectedStatus = 404

        # If it fails here, it most probably means given layer does not have sphinx index available
        link = '/rest/services/all/SearchServer?features=' + layer + '&bbox=600818.7808825106,197290.49919797093,601161.2808825106,197587.99919797093&type=featuresearch&searchText=dummy'
        resp = self.testapp.get(link, status=expectedStatus)
        # If there are no features, we don't expect a sphinx index present
        if expectedStatus == 404:
            assert 'unknown local index' in resp.body

    def checkPrimaryKeyColumnTypeMapping(self, layerId, featureId, model, primaryKeyColumn):
        schema = 'public' if 'schema' not in model.__table_args__ else model.__table_args__['schema']
        assert featureId is not None, 'No feature was found in table %s for layer %s' % (
            schema + '.' + model.__tablename__, layerId)
        pythonType = primaryKeyColumn.type.python_type
        assert type(featureId) == pythonType, 'Expected %s; Got: %s; For layer %s and GeoTable %s' % (
            pythonType, type(featureId), layerId, schema + '.' + model.__tablename__)


def test_all_htmlpopups():
    with LayersChecker() as lc:
        for layer, feature, extended in lc.ilayersWithFeatures():
            yield lc.checkHtmlPopup, layer, feature, extended


def test_all_legends():
    with LayersChecker() as lc:
        for layer in lc.ilayers(hasLegend=True):
            yield lc.checkLegend, layer


def test_all_ids_mapping():
    with LayersChecker() as lc:
        for layerId, featureId, model, primaryKeyColumn in lc.ilayersAllModels():
            yield lc.checkPrimaryKeyColumnTypeMapping, layerId, featureId, model, primaryKeyColumn


def test_all_legends_images():
    # Get list of layers from existing legend images
    legendsPath = os.getcwd() + '/chsdi/static/images/legends/'
    legendNames = os.listdir(legendsPath)
    parseLegendNames = lambda x: x[:-4] if 'big' not in x else x[:-8]
    legendImages = list(set(map(parseLegendNames, legendNames)))

    with LayersChecker() as lc:
        for layer in lc.ilayers(hasLegend=True):
            yield lc.checkLegendImage, layer, legendImages


def test_all_searchable_layers():
    with LayersChecker() as lc:
        for layer in lc.ilayers(searchable=True):
            yield lc.checkSearch, layer
