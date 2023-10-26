import os
import psycopg2
import psycopg2.extras
import requests
import json
from data_export import sheet2json, gql2json, upload_data
from datetime import datetime, timezone, timedelta
from configs import homepage_data

def election2024():
    # just for 2024 election homepage json
    #DATA_SERVICE = os.environ['DATA_SERVICE']
    #WHORU_BUCKET = os.environ['WHORU_BUCKET']
    WHORU_BUCKET = 'whoareyou-gcs-dev.readr.tw'
    #gql_endpoint = os.environ['WHORU_GQL_ENDPOINT']
    gql_endpoint = 'https://openrelationship-gql-dev-4g6paft7cq-de.a.run.app/api/graphql'
    gql_string = """
query GetPresidents {
  personElections(
    orderBy:{ number: asc },
    where: {
      election: {id: { equals: 85 } },
      mainCandidate: null
    }) {
    id
    number
    person_id {
      id
      name
    }
    politicsCount(
      where: {
        status: { equals: "verified" },
        reviewed: { equals: true },
      })
    politics(
      where: {
        status: { equals: "verified" },
        reviewed: { equals: true }
      }) {
        id
        desc
        politicCategory {
          id
          name
        }
        positionChangeCount
        expertPointCount
        factCheckCount
        repeatCount
    }
  }
}
"""
    candidate_statistics = {}
    all_candidates = gql2json(gql_endpoint, gql_string)
    #==============================================
    get_categories = """
query { politicCategories {
  id
  name
} }
    """
    categories = gql2json(gql_endpoint, get_categories)

    category_base = {}
    for category in categories["politicCategories"]:
        category_base[category["name"]] = 0
    #==============================================
    for candidate in all_candidates["personElections"]:
        candidate_data = {}
        candidate_data["categories_count"] = category_base
        candidate_data["positionChangeCount"] = 0
        candidate_data["expertPointCount"] = 0
        candidate_data["factCheckCount"] = 0
        candidate_data["repeatCount"] = 0
        candidate_data["politicsCount"] = candidate["politicsCount"]
        if "politics" in candidate:
            for policy in candidate["politics"]:
                candidate_data["positionChangeCount"] += policy["positionChangeCount"]
                candidate_data["expertPointCount"] += policy["expertPointCount"]
                candidate_data["factCheckCount"] += policy["factCheckCount"]
                candidate_data["repeatCount"] += policy["repeatCount"]
                if policy is not None and "politicCategory" in policy and policy["politicCategory"] is not None and "name" in policy["politicCategory"] and policy["politicCategory"]["name"] in candidate_data["categories_count"]:
                    candidate_data["categories_count"][policy["politicCategory"]["name"]] += 1
        candidate_statistics[candidate["person_id"]["name"]] = candidate_data
    dest_file = "json/landing_statitics.json"
    upload_data(WHORU_BUCKET, json.dumps(candidate_statistics, ensure_ascii=False).encode('utf8'), 'application/json', dest_file)
    return "ok"

def factcheck_data():
    #DATA_SERVICE = os.environ['DATA_SERVICE']
    WHORU_BUCKET = os.environ['WHORU_BUCKET']
    #WHORU_BUCKET = 'whoareyou-gcs-dev.readr.tw'
    gql_endpoint = os.environ['WHORU_GQL_ENDPOINT']
    #gql_endpoint = 'https://openrelationship-gql-dev-4g6paft7cq-de.a.run.app/api/graphql'
    get_categories = """
query { politicCategories {
  id
} }
    """
    categories = gql2json(gql_endpoint, get_categories)
    for category in categories["politicCategories"]:
        print(category['id'])
        gql_string = """
query GetPresidents {
  personElections(
    orderBy:{ number: asc },
    where: {
      election: {id: { equals: 85 } },
      mainCandidate: null
    }) {
    id
    number
    person_id {
      id
      name
    }
    politicsCount(
      where: {
        status: { equals: "verified" },
        reviewed: { equals: true },
        politicCategory: { id: { equals: %s } }
      })
    politics(
      where: {
        status: { equals: "verified" },
        reviewed: { equals: true }
        politicCategory: { id: { equals: %s } }
      }) {
        id
        desc
        politicCategory {
          id
          name
        }
        positionChange {
          id
          isChanged
          factcheckPartner {
            id
            name
          }
        }
        positionChangeCount
        expertPoint {
          id
          expertPointSummary
          expert
        }
        expertPointCount
        factCheck {
          id
          factCheckSummary
          checkResultType
          factcheckPartner {
            id
            name
          }
        }
        factCheckCount
        repeat {
          id
          repeatSummary
          factcheckPartner {
            id
            name
          }
        }
        repeatCount
    }
  }
}
""" % (category['id'], category['id'])
        json_data = gql2json(gql_endpoint, gql_string)
        dest_file = """json/landing_factcheck_%s.json""" % (category["id"])
        upload_data(WHORU_BUCKET, json.dumps(json_data, ensure_ascii=False).encode('utf8'), 'application/json', dest_file)
    return "ok"

if __name__=="__main__":
    election2024()
