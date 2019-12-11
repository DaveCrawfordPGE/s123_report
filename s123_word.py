import docxtpl


def set_up_docx_inline(url):
    from io import BytesIO
    from requests import get as requestsget

    response = requestsget(url)
    img = BytesIO(response.content)
    return img

# from working script for pdf
# def set_up_docx_inline(url):
#     from io import BytesIO
#     from requests import get as requestsget
#
#     response = requestsget(url)
#     img = BytesIO(response.content)
#     return img


def find_attachment(att_res, keyword):
    try:
        for attachment in att_res:
            if keyword in attachment['KEYWORDS']:
                return attachment['DOWNLOAD_URL']
    except:
        return None

def find_related_table(fp_object, layername):
    try:
        for rel in fp_object.related_data:
            if layername in rel.layer_name:
                return rel
    except:
        return None


def df_to_table_word(df):
    return df.to_dict('records')


def repeat_to_table(fp_object, rel_table_name):
    # TODO - if there's nothing, add n/as
    returner = None
    for rel in fp_object.related_data:
        if rel.layer_name == rel_table_name:
            returner =  rel.to_sdf().to_dict('records')
    if returner == None:
        print('Nothing by that name here')
    return returner


def fp_to_docx(fp_object, template, out_folder, doc_name):
    from docx.shared import Mm, Inches
    from os.path import join
    doc_template = docxtpl.DocxTemplate(template)
    in_vars = doc_template.get_undeclared_template_variables()
    dict_vars = {}
    for var in in_vars:
        try:
            if fp_object.fm_main[var]['domain_trans']:
                try:
                    dict_vars[var] = fp_object.fm_main[var]['domain_trans'][fp_object.attributes[var]]
                except KeyError:
                    dict_vars[var] = fp_object.attributes[var]
            else:
                dict_vars[var]=fp_object.attributes[var]
        except KeyError:
            if 'att' in var:
                print('\tattachment {}'.format(var))
                if 'att20_' in var:
                    att_url = find_attachment(fp_object.att_res, var.replace('att20_',''))
                    if att_url == None:
                        pass
                    else:
                        dict_vars[var] = docxtpl.InlineImage(doc_template, set_up_docx_inline(att_url), height=Mm(20))
                else:
                    att_url = find_attachment(fp_object.att_res, var.replace('att_',''))
                    if att_url == None:
                        pass
                    else:
                        dict_vars[var] = docxtpl.InlineImage(doc_template, set_up_docx_inline(att_url),width=Inches(6))
            elif 'rel_' in var:
                related_set = find_related_table(fp_object, var.replace('rel_', ''))
                if len(related_set.features) > 0:
                    dict_vars[var] = related_set.return_sdf().to_dict('records')

            else:
                print('\tnon-attribute: {}'.format(var))
    doc_template.render(dict_vars)
    if '.docx' not in doc_name:
        doc_name = doc_name + '.docx'
    print('\tsaving...')
    return doc_template.save(join(out_folder, doc_name))
