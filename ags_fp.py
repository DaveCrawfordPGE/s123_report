class FeatPackage(object):
    def __init__(self):
        self.main_fset = None
        self.fields_main = None
        self.fm_main = {}
        self.attributes = {}
        self.geometry = {}
        self.has_attachments = False
        self.has_related_tables = False
        self.att_res = None
        self.layer_name = None


class AgolFeatPackage(FeatPackage):
    def __init__(self):
        FeatPackage.__init__(self)
        self.relationships = []
        self.related_data = []
        self.exclude_fields = []
        self.info_fields = {}

    def __str__(self):
        return str(self.attributes)

    def build_field_order(self, simplify=True):
        from pandas import DataFrame
        att_alias = []

        if simplify:
            list_fields = [field for field in list(self.fm_main.keys()) if field not in self.exclude_fields]
        else:
            list_fields = [field for field in list(self.fm_main.keys())]
        for field in list_fields:
            alias = self.fm_main[field]['alias']
            try:
                value = self.fm_main[field]['domain_trans'][self.attributes[field]]
            except KeyError:
                value = self.attributes[field]
            att_alias.append([alias, value])
        return DataFrame(att_alias, columns=['Field', 'Value'])

    def grab_att_links(self):
        return [info['DOWNLOAD_URL'] for info in self.att_res]

    def find_attachment(self, keyword):
        try:
            for attachment in self.att_res:
                if keyword in attachment['KEYWORDS']:
                    return attachment
        except:
            return None


class S123FeatPackage(AgolFeatPackage):
    def __init__(self):
        AgolFeatPackage.__init__(self)
        self.user_info = {}
        self.portal_info = {}
        self.survey_info = {}
        self.feature = {}
        self.response = {}
        self.apply_edits = {}


class RelatedSet(object):
    def __init__(self):
        self.layer_name = None
        self.features = []
        self.has_attachments = False
        self.fields = []
        self.exclude_fields = []

    def return_fset(self):
        try:
            from arcgis.features import FeatureSet
            fset = FeatureSet(self.features)
            fset.fields = self.fields
            return fset
        except:
            raise Exception('You might not have the arcgis module')

    def return_sdf(self, simplify=True):
        try:
            from arcgis.features import FeatureSet
            if simplify:
                out_fields = [field['name'] for field in self.fields if field['name'] not in self.exclude_fields]
            else:
                out_fields = [field['name'] for field in self.fields]
            return FeatureSet(self.features).sdf[out_fields]
        except:
            raise Exception('You might not have the arcgis module')


class Utils(object):
    def __init__(self):
        pass

    def agol_to_local_time(time_value):
        from datetime import datetime
        ts = int(time_value)
        try:
            return datetime.utcfromtimestamp(ts).strftime('%m-%d-%Y')
        except:
            return datetime.utcfromtimestamp(ts/1000).strftime('%m-%d-%Y')

    @staticmethod
    def from_webhook(webhook_response):
        temp_object = S123FeatPackage()
        res_keys = list(webhook_response.keys())
        if 'feature' in res_keys:
            temp_object.attributes = webhook_response['feature']['attributes']
            temp_object.geometry = webhook_response['feature']['geometry']

        if 'surveyInfo' in res_keys:
            temp_object.survey_info = webhook_response['surveyInfo']

        if 'userInfo' in res_keys:
            temp_object.user_info = webhook_response['userInfo']
        return temp_object

    @staticmethod
    def from_layer(layer, sql_query):

        """modified because of spotty functionality in .container property"""
        temp_object = AgolFeatPackage()
        temp_object.main_fset = layer.query(sql_query)
        if len(temp_object.main_fset) > 1:
            raise Exception('More than 1 feature')
        temp_object.fields_main = temp_object.main_fset.fields
        temp_object.fm_main = {}
        for field in temp_object.fields_main:
            temp_object.fm_main[field['name']] = {'alias' : field['alias'], 'domain_trans' : {}}
            if field['domain']:
                if field['domain']['type']=='codedValue':
                    for dv in field['domain']['codedValues']:
                        temp_object.fm_main[field['name']]['domain_trans'][dv['code']]=dv['name']

        for field in temp_object.fields_main:
            if field['type'] == 'esriFieldTypeDate':
                for feature in temp_object.main_fset:
                    feature.set_value(field['name'], Utils.agol_to_local_time(feature.get_value(field['name'])))

        if layer.container == None:
            from arcgis.features import FeatureLayerCollection
            container = FeatureLayerCollection('/'.join(layer.url.split('/')[0:-1]), layer._gis)
        else:
            container = layer.container

        temp_object.attributes = temp_object.main_fset.features[0].attributes
        temp_object.geometry = temp_object.main_fset.features[0].geometry

        if layer.properties.hasAttachments:
            temp_object.has_attachments = True
            temp_object.att_res = layer.attachments.search(sql_query)

        temp_object.layer_name = layer.properties.name.replace('_',' ')

        if container.properties.editorTrackingInfo['enableEditorTracking']:
            temp_object.exclude_fields += dict(layer.properties.editFieldsInfo).values()
            temp_object.exclude_fields.append(layer.properties.objectIdField)
            temp_object.exclude_fields.append(layer.properties.globalIdField)
        for fieldname in list(temp_object.fm_main.keys()):
            if fieldname in ['Header','Subtext']:
                temp_object.exclude_fields.append(fieldname)
                temp_object.info_fields[fieldname]=temp_object.fm_main[fieldname]
        if len(layer.properties.relationships) > 0:
            temp_object.has_related_tables = True
            temp_object.relationships = layer.properties.relationships

            all_tab_layers = container.layers + container.tables

            for relater in temp_object.relationships:
                tempset = RelatedSet()
                temp_rel_query = layer.query_related_records(temp_object.attributes[layer.properties.objectIdField],
                                                             relater['id'])
                tempset.fields = temp_rel_query['fields']
                if len(temp_rel_query['relatedRecordGroups']) > 0:
                    tempset.features = temp_rel_query['relatedRecordGroups'][0]['relatedRecords']
                else:
                    tempset.features = []
                    # TODO - implement some N/As

                for tab_layer in all_tab_layers:
                    if tab_layer.url.split('/')[-1] == str(relater['id']):
                        templayer = tab_layer

                if templayer.properties.hasAttachments:
                    tempset.has_attachments = True
                tempset.layer_name = templayer.properties.name
                if container.properties.editorTrackingInfo['enableEditorTracking']:
                    tempset.exclude_fields += dict(templayer.properties.editFieldsInfo).values()
                tempset.exclude_fields.append(templayer.properties.objectIdField)
                tempset.exclude_fields.append(templayer.properties.globalIdField)
                if 'parentglobalid' in [field['name'] for field in tempset.fields]:
                    tempset.exclude_fields.append('parentglobalid')

                temp_object.related_data.append(tempset)

        return temp_object

































































