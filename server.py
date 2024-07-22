from flask import Flask, request
from data_export import sheet2json, gql2json, upload_data
from rss_generator import gql2rss
from scheduled_update import status_update
from podcast import mirrorvoice_filter
import sitemap
import os
import json
import pytz
import utils.query as query

from datetime import datetime, timedelta
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from sitemap import generate_web_sitemaps, generate_sitemap_index, generate_news_sitemaps

app = Flask(__name__)
gql_endpoint = os.environ['GQL_ENDPOINT']
BUCKET = os.environ.get('BUCKET', None)

@app.route("/gql_to_json")
def generate_json_from_gql():
	gql_string = request.args.get('gql_string')
	bucket = request.args.get('bucket')
	dest_file = request.args.get('dest_file')
	alt_gql_endpoint = request.args.get('gql_endpoint')
	if alt_gql_endpoint:
		gql_endpoint = alt_gql_endpoint
	else:
		gql_endpoint = os.environ['GQL_ENDPOINT']
	json_data = gql2json(gql_endpoint, gql_string)
	upload_data(bucket, json.dumps(json_data, ensure_ascii=False).encode('utf8'), 'application/json', dest_file)
	return "ok"

@app.route("/sheet_to_json")
def generate_json_from_sheet():
	sheet_url = request.args.get('sheet_url')
	sheet_name = request.args.get('sheet_name')
	bucket = request.args.get('bucket')
	dest_file = request.args.get('dest_file')
	json_data = sheet2json(sheet_url, sheet_name)
	upload_data(bucket, json.dumps(json_data, ensure_ascii=False).encode('utf8'), 'application/json', dest_file)
	return "ok"
    
@app.route("/cron_update")
def scheduled_publish():
    return_message = status_update()
    return return_message

@app.route("/sitemap/generator", methods=['POST'])
def sitemap_generator():
    '''
        You should provide two arguments in payload json
        (1) target_objects: eg.['show', 'topic', ...etc], you cand find them at CMS
        (2) chunk_size[opt]: Upper limit for a single sitemap xml
    '''
    msg = request.get_json()
    target_objects = msg.get('target_objects', None)
    chunk_size = msg.get('chunk_size', 1000)
    if target_objects==None:
        return "query parameters error"
    
    objects = [obj.strip() for obj in target_objects]

    app = os.environ.get('PROJECT_NAME', 'mnews')
    sitemap_news_days = os.environ.get('SITEMAP_NEWS_DAYS', 2)
    timezone  = pytz.timezone('Asia/Taipei')

    ### Generate sitemap for website
    sitemap_files = []
    folder = os.path.join('rss', 'sitemap')
    
    for object_name in objects:
        # post should be handled by other method
        if object_name == 'post':
            continue
        gql_string = query.sitemap_object_mapping[object_name]
        gql_result = query.gql_fetch(gql_endpoint=gql_endpoint, gql_string=gql_string)

        xml_strings = generate_web_sitemaps(
            rows = gql_result['items'],
            app = app,
            object_name = object_name,
            chunk_size = chunk_size
        )
        for index, sitemap_xml in enumerate(xml_strings):
            filename = f'sitemap_{object_name}{index+1}.xml'
            upload_data(BUCKET, sitemap_xml, "Application/xml", os.path.join(folder, filename))
            
            time  = datetime.now(timezone)
            lastmod = time.strftime("%Y-%m-%d")
            sitemap_files.append({
                'filename': os.path.join(folder, filename),
                'lastmod': lastmod
            })
    if len(sitemap_files)>0:
        sitemap_index_xml = generate_sitemap_index(sitemap_files)
        upload_data(BUCKET, sitemap_index_xml, "Application/xml", os.path.join(folder, 'sitemap_index_web_others.xml'))
    
    ### Generate sitemap for google tab news
    sitemap_files = []
    object_name = 'post'
    if object_name in objects:
        alias_object_name = 'story'
        time  = datetime.now(timezone)
        # use ISO 8601 time format
        lastmod = time.isoformat()
        previous_time = time - timedelta(hours=int(sitemap_news_days)*24)
        publish_gt_time = previous_time.isoformat()
        # lastmod = time.strftime("%Y-%m-%d")
        # publish_gt_time = previous_time.strftime("%Y-%m-%d")

        # In news sitemap, practically you can only parse the posts within 2 days
        gql_string = ""
        if app == 'mnews':
            gql_string = query.get_allPosts_string(publish_gt_time)
        else:
            gql_string = query.get_Posts_string(publish_gt_time)
        
        print(gql_string)
        
        gql_result = query.gql_fetch(gql_endpoint=gql_endpoint, gql_string=gql_string)
        xml_strings = generate_news_sitemaps(
                rows = gql_result['items'],
                app = app,
                language = 'zh-tw',
                chunk_size = chunk_size
            )
        for index, sitemap_xml in enumerate(xml_strings):
            filename = f'sitemap_{alias_object_name}{index+1}.xml'
            upload_data(BUCKET, sitemap_xml, "Application/xml", os.path.join(folder, filename))
            sitemap_files.append({
                    'filename': os.path.join(folder, filename),
                    'lastmod': lastmod
            })
        if len(sitemap_files)>0:
            sitemap_index_xml = generate_sitemap_index(sitemap_files)
            if app == 'mnews': 
                upload_data(BUCKET, sitemap_index_xml, "Application/xml", os.path.join(folder, 'sitemap_index_newstab.xml'))
            else:
                upload_data(BUCKET, sitemap_index_xml, "Application/xml", os.path.join(folder, 'index.xml'))
    return "ok"
    

@app.route("/k6_to_rss")
def generate_rss_from_k6():
    gql_string = request.args.get('gql_string')
    bucket = request.args.get('bucket')
    schema_type = request.args.get('schema_type')
    dest_file = request.args.get('dest_file')
    relatedPost = request.args.get('relatedPost')
    rm_ytbiframe = request.args.get('rm_ytbiframe')
    relatedPost_number = request.args.get('relatedPost_number')
    rss_data = gql2rss(gql_endpoint, gql_string, schema_type, relatedPost, rm_ytbiframe, relatedPost_number)

    if rss_data:
        upload_data(bucket, rss_data, 'application/xml', dest_file)
        return "ok"
    return "fail"

@app.route("/mirrormedia_podcast")
def get_podcasts_from_mirrorvoice():
    feedurl = request.args.get('feed_url', default = 'https://feed.mirrorvoice.com.tw/rss/mnews.xml')
    bucket = request.args.get('bucket')
    dest_file = request.args.get('dest_file')
    author_filter = []
    podcast_json = mirrorvoice_filter(author_filter, feedurl)
    json_data = json.dumps(podcast_json, ensure_ascii=False).encode('utf8')
    upload_data(bucket, json_data, 'application/json', dest_file)
    return "ok"

if __name__ == "__main__":
    app.run()

