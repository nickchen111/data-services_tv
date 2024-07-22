import os
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

def gql_fetch(gql_endpoint, gql_string, gql_variable=None):
    gql_transport = AIOHTTPTransport(url=gql_endpoint)
    gql_client = Client(transport=gql_transport,
                        fetch_schema_from_transport=True)
    if gql_variable:
        json_data = gql_client.execute(gql(gql_string))
    else:
        json_data = gql_client.execute(gql(gql_string), variable_values=gql_variable)
    return json_data

gql_allTags = """
query AllTags {
    items: allTags(sortBy: [updatedAt_DESC], where: {slug_not: null}) {
        id
        slug
        name
        updatedAt
        createdAt
    }
}
"""

gql_allTopics = """
query AllTopics {
    items: allTopics(sortBy: [updatedAt_DESC], where: { slug_not: null, state: published }) {
        id
        slug
        updatedAt
        createdAt
    }
}
"""

gql_allShows = """
query AllShows {
    items: allShows(sortBy: [updatedAt_DESC], where: { slug_not: null }) {
        id
        slug
        updatedAt
        createdAt
    }
}
"""

def get_allPosts_string(publishTime: str):
    gql_tv_allPosts = f"""
    query AllPosts {{
        items: allPosts(
            where: {{ slug_not: null, state: published, publishTime_gt: "{publishTime}" }}
            sortBy: [publishTime_DESC]
        ) {{
            id
            slug
            name
            publishTime
        }}
    }}
    """
    return gql_tv_allPosts

def get_Posts_string(publishTime: str):
    gql_posts = f"""
    query {{
        items: posts(
            where: {{ 
                state: {{equals:"published"}}, publishedDate: {{gt:"{publishTime}"}} 
            }}
            orderBy: {{publishedDate : desc}}
        ) {{
            id
            slug
            title
            publishedDate
        }}
    }}
    """
    return gql_posts

sitemap_object_mapping = {
    'show': gql_allShows,
    'topic': gql_allTopics,
    'tag': gql_allTags
}