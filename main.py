import http
import json

url = '{{url}}'


def main():
    open_api = get_open_api()
    postman = get_postman(open_api)
    print('final:', postman)


def get_postman(open_api):
    postman = {
        'info':
            {
                '_postman_id': 'b0a0b0a0-b0a0-b0a0-b0a0-b0a0b0a0b0a0',
                'name': open_api['info']['title'],
                'description': open_api['info']['description'],
                'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json',
            },
        'item': []
    }

    for path, item in open_api['paths'].items():
        postman_path = convert_path(path)
        for method, details in item.items():
            request_query = []
            request_variable = []
            postman_responses = []

            if 'parameters' in details:
                for param in details['parameters']:
                    parameter = resolve_parameter(param, open_api)

                    if parameter['in'] == 'query':
                        request_query.append(create_parameter(parameter))
                    elif parameter['in'] == 'path':
                        request_variable.append(create_parameter(parameter))

            request = create_request(method, postman_path, request_query, request_variable)

            if 'responses' in details:
                for code, response in details['responses'].items():
                    current_response = {
                        'name': '{} {}'.format(details['summary'], code),
                        'originalRequest': request,
                        'status': http.HTTPStatus(int(code)).phrase,
                        'code': code,
                        # TODO: Add proper preview language
                        '_postman_previewlanguage': 'json',
                        'header': get_response_headers(response),
                        'cookie': [],
                        'body': create_response_body(response, open_api),
                    }
            postman_item = {
                'name': details['summary'],
                'request': request,
                'response': postman_responses,
            }

            if request_query:
                postman_item['request']['url']['query'] = request_query
            if request_variable:
                postman_item['request']['url']['variable'] = request_variable

            postman['item'].append(postman_item)
        break

    return postman


def resolve_ref(ref, open_api):
    # TODO currently only supports references to open api components
    parts = ref.split('/')
    result = open_api
    if parts[0] == '#':
        for part in parts[1:]:
            result = result[part]
        return result
    print('Error: Invalid reference')
    return None


def get_formatted_prop_value(prop_value, default):
    if 'example' in prop_value:
        return prop_value['example']
    return default


def process_property(prop_value):
    type_mapping = {
        'string': 'string',
        'integer': 0,
        'boolean': False,
        'array': [],
        'object': {},
    }
    if prop_value['type'] not in type_mapping:
        print('Error: Unknown type -', prop_value['type'])
        raise Exception('Unknown type')

    return get_formatted_prop_value(prop_value, type_mapping[prop_value['type']])


def resolve_and_update_properties(j, key_dict, open_api):
    new_properties = resolve_ref(j, open_api)
    for prop, prop_value in new_properties['properties'].items():
        new_prop = process_property(prop_value)
        if isinstance(key_dict, list):
            key_dict.append(new_prop)
        elif isinstance(key_dict, dict):
            key_dict[prop] = new_prop


def create_response_body(response, open_api):
    # TODO: Currently only supports application/JSON responses
    # DOING: finishing this
    try:
        body = {}
        for key, value in response['content']['application/json']['schema']['properties'].items():
            key_dict = {}
            if 'type' in value:
                if value['type'] == 'object':
                    key_dict = {}
                elif value['type'] == 'array':
                    key_dict = []
            for i, j in value.items():
                if i == '$ref':
                    resolve_and_update_properties(j, key_dict, open_api)
                    body[key] = key_dict
                elif i == 'items':
                    for k, l in j.items():
                        if k == '$ref':
                            resolve_and_update_properties(l, key_dict, open_api)
                    body[key] = key_dict
            print('body thing', body)
    except Exception as e:
        print('Something went wrong:', e)
        return ''


def transform_properties(properties):
    transformed_properties = {}

    for key, value in properties.items():
        if 'type' in value and value['type'] == 'object':
            print('asd')
            if '$ref' in value:
                transformed_properties[key] = {'$ref': value['$ref']}
                for sub_key, sub_value in value.items():
                    if sub_key != '$ref':
                        transformed_properties[key][sub_key] = sub_value
            else:
                transformed_properties[key] = transform_properties(value)
        if 'type' in value and value['type'] == 'array':
            transformed_properties[key] = []
            if 'items' in value:
                for sub_key, sub_value in value['items'].items():
                    transformed_properties[key].append(transform_properties({sub_key: sub_value}))
        else:
            transformed_properties[key] = value

    return transformed_properties


def get_response_headers(response):
    # TODO: Add all headers
    headers = [{
        'key': 'Content-Type',
        'value': list(response['content'].keys())[0]
    }]
    return headers


def create_request(method, path, request_query, request_variable):
    request = {
        'method': method.upper(),
        'header': [],
        'url': {
            'raw': url + path,
            'host': [url],
            'path': path.split('/'),
        }
    }

    if request_query:
        request['url']['query'] = request_query
    if request_variable:
        request['url']['variable'] = request_variable

    return request


def resolve_parameter(parameter, open_api):
    if '$ref' in parameter:
        print(resolve_ref(parameter['$ref'], open_api))
        return resolve_ref(parameter['$ref'], open_api)
    return parameter


def create_parameter(parameter):
    # TODO: Add description for parameter types and schemas
    return {
        'key': parameter['name'],
        'value': None,
        'description': parameter['description'],
        'disabled': True,
    }


def get_open_api():
    try:
        with open('open_api.json') as open_api_file:
            return json.load(open_api_file)
    except FileNotFoundError as e:
        print(f"Error: File 'open_api.json' not found. {str(e)}")
    except json.JSONDecodeError as e:
        print(f"Error: File 'open_api.json' is not a valid JSON file. {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")
    exit(0)


def convert_path(path):
    return path.replace('{', ':').replace('}', '')


if __name__ == '__main__':
    p = {
        "data": {
            "type": "array",
            "items": {
                "$ref": "#/components/schemas/FarmInfo",
                "something": "hi"
            }
        },
        "meta": {
            "$ref": "#/components/schemas/Meta",
            "hello": "world"
        },
        "links": {
            "$ref": "#/components/schemas/Links",
            "foo": "bar"
        }
    }
    new = transform_properties(p)
    main()
