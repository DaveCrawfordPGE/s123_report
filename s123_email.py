def get_file_format(content_type):
    temp_dict = {'image/jpeg': 'jpeg',
                 'image/png': 'png',
                 'application/octet-stream': 'pdf'}
    try:
        return temp_dict[content_type]
    except KeyError:
        return content_type.replace('image/', '')


def set_up_MIME_IMAGE(url, file_format):
    from io import BytesIO
    from requests import get as requestsget
    from PIL import Image
    from email.mime.image import MIMEImage

    stream_bytes = BytesIO()
    response = requestsget(url)
    img = Image.open(BytesIO(response.content))
    img.save(stream_bytes, file_format)
    stream_bytes.seek(0)
    img_obj = stream_bytes.read()

    return MIMEImage(img_obj)


def attach_image_inline(msg_root, msg_template, url, tag, file_format='jpeg'):
    '''Sets up image attachment in email'''
    mime_img = set_up_MIME_IMAGE(url, file_format)
    mime_img.add_header('Content-ID', '<{}>'.format(tag))
    msg_root.attach(mime_img)

    html_tag = '''<br><b>{}</b><br><br><img src="cid:{}"><br>'''.format(tag, tag)
    return msg_template + html_tag


def add_table_to_template(template, df, table_title):
    formatted_df = df.to_html(index=False).replace('<th>',
                                        '<th style = "background-color: #777;border: 1px solid #ddd;padding: 8px;">') \
        .replace('\n', '').replace('<table border="1" class="dataframe">',
                                   '	<table border="1" align="center" width=80% class="dataframe" style="border-collapse:collapse; position: relative; padding:15px; background-color:#fff">').replace(
        '<td>', '<td style ="border: 1px solid #ddd;padding: 8px;">')

    html = """  <br>
                <h3 style="text-align:center;"><b>{}</b></h3>
                {}
                <br>
                """.format(table_title, formatted_df)
    return template + html


def survey123_to_email(feat_ob, display_field, email_field):
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    #from jinja2 import Environment
    mp_msg = MIMEMultipart()

    if len(feat_ob.info_fields) == 0:
        info_to_add = False
    else:
        info_to_add = True
        info_adds = list(feat_ob.info_fields.keys())

    TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
    <title>Survey Report</title>
      <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css">
      <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js"></script>
      <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js"></script>

      <style>
    table {
      border-collapse: collapse;
    }
     table, th, td {
      border: 1px solid black;
      text-align: center;
    }
      </style>

    """
    TEMPLATE += """
    </head>
    <body>
        <h1 style="text-align:center;">{}</h1>
        <h2 style="text-align:center;">{}</h2>
    """.format(feat_ob.layer_name, feat_ob.attributes[display_field])

    if info_to_add and 'Header' in info_adds:
        TEMPLATE += """
        <p style="text-align:center;">{}</p>
        """.format(feat_ob.info_fields['Header'])

    TEMPLATE = add_table_to_template(TEMPLATE, feat_ob.build_field_order(), 'Main Feature')

    if info_to_add and 'Subtext' in info_adds:
        TEMPLATE += """
        <p style="text-align:center;">{}</p>
        """.format(feat_ob.info_fields['Subtext'])


    if (feat_ob.att_res):
        for att in feat_ob.att_res:
            TEMPLATE = attach_image_inline(mp_msg, TEMPLATE, att['DOWNLOAD_URL'], att['KEYWORDS'],
                                           get_file_format(att['CONTENTTYPE']))
    if (feat_ob.related_data):
        for rel_data in feat_ob.related_data:
            TEMPLATE = add_table_to_template(TEMPLATE, rel_data.return_sdf(), rel_data.layer_name)
    TEMPLATE += """</body>
                </html>
                """
    # mst_template = MIMEText(
    #     Environment().from_string(TEMPLATE).render(
    #         title='Feature Report',
    #
    #     ), "html"
    # )
    mst_template = MIMEText(TEMPLATE,'html')
    mp_msg.attach(mst_template)
    return mp_msg



