"""Tests for the GraphQL Response Parser.

At the moment we use the Star Wars schema which is fetched each time from the
server endpoint. In future it would be better to store this schema in a file
locally.
"""
import copy
from gql.response_parser import ResponseParser
import pytest
import requests
from gql import Client
from gql.transport.requests import RequestsHTTPTransport

class Capitalize():
    @classmethod
    def parse_value(self, value: str):
        return value.upper();

@pytest.fixture
def schema():
    request = requests.get('http://swapi.graphene-python.org/graphql',
                           headers={
                               'Host': 'swapi.graphene-python.org',
                               'Accept': 'text/html',
                           })
    request.raise_for_status()
    csrf = request.cookies['csrftoken']

    client = Client(
        transport=RequestsHTTPTransport(url='http://swapi.graphene-python.org/graphql',
                                        cookies={"csrftoken": csrf},
                                        headers={'x-csrftoken':  csrf}),
        fetch_schema_from_transport=True
    )

    return client.schema

def test_scalar_type_name_for_scalar_field_returns_name(schema):
    parser = ResponseParser(schema)
    schema_obj = schema.get_query_type().fields['film']

    assert parser._get_scalar_type_name(schema_obj.type.fields['releaseDate']) == 'DateTime'


def test_scalar_type_name_for_non_scalar_field_returns_none(schema):
    parser = ResponseParser(schema)
    schema_obj = schema.get_query_type().fields['film']

    assert parser._get_scalar_type_name(schema_obj.type.fields['species']) is None

def test_lookup_scalar_type(gql_schema):
    parser = ResponseParser(gql_schema)

    assert parser._lookup_scalar_type(["film"]) is None
    assert parser._lookup_scalar_type(["film", "releaseDate"]) == 'DateTime'
    assert parser._lookup_scalar_type(["film", "species"]) is None

def test_lookup_scalar_type_in_mutation(schema):
    parser = ResponseParser(schema)

    assert parser._lookup_scalar_type(["createHero"]) is None
    assert parser._lookup_scalar_type(["createHero", "hero"]) is None
    assert parser._lookup_scalar_type(["createHero", "ok"]) == 'Boolean'

def test_parse_response(schema):
    custom_scalars = {
        'DateTime': Capitalize
    }
    parser = ResponseParser(schema, custom_scalars)

    response = {
        'film': {
            'id': 'some_id',
            'releaseDate': 'some_datetime',
        }
    }

    expected = {
        'film': {
            'id': 'some_id',
            'releaseDate': 'SOME_DATETIME',
        }
    }

    assert parser.parse(response) == expected
    assert response['film']['releaseDate'] == 'some_datetime' # ensure original response is not changed

def test_parse_response_containing_list(schema):
    custom_scalars = {
        'DateTime': Capitalize
    }
    parser = ResponseParser(schema, custom_scalars)

    response = {
        "allFilms": {
            "edges": [{
                "node": {
                    'id': 'some_id',
                    'releaseDate': 'some_datetime',
                }
            },{
                "node": {
                    'id': 'some_id',
                    'releaseDate': 'some_other_datetime',
                }
            }]
        }
    }

    expected = copy.deepcopy(response)
    expected['allFilms']['edges'][0]['node']['releaseDate'] = "SOME_DATETIME"
    expected['allFilms']['edges'][1]['node']['releaseDate'] = "SOME_OTHER_DATETIME"

    result = parser.parse(response)

    assert result == expected
    expected['allFilms']['edges'][0]['node']['releaseDate'] = "some_datetime"
    expected['allFilms']['edges'][1]['node']['releaseDate'] = "some_other_datetime"
