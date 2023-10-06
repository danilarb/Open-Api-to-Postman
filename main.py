import http
import json

url = '{{url}}'


def main():
    open_api = get_open_api()
    postman = get_postman(open_api)
    with open('postmantrial.json', 'w') as file:
        json.dump(postman, file, ensure_ascii=True, indent=4)
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
                        # 'body': create_response_body(response, open_api),
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
        # break

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


def resolve_and_update_properties(ref, key_dict, open_api):
    new_properties = resolve_ref(ref, open_api)
    item = {}
    for prop, prop_value in new_properties['properties'].items():
        if 'items' in prop_value:
            items = {}
            if 'type' in prop_value['items']:
                if prop_value['items']['type'] == 'array':
                    items = []
            if '$ref' in prop_value['items']:
                resolve_and_update_properties(prop_value['items']['$ref'], items, open_api)
        new_prop = process_property(prop_value)
        item[prop] = new_prop
    if isinstance(key_dict, dict):
        key_dict.update(item)
    else:
        key_dict.append(item)


def create_response_body(response, open_api):
    # TODO: Currently only supports application/JSON responses
    # DOING: finishing this
    try:
        body = {}
        if 'properties' in response['content']['application/json']['schema']:
            for key, value in response['content']['application/json']['schema']['properties'].items():
                key_dict = {}
                if 'type' in value:
                    if value['type'] == 'array':
                        key_dict = []
                    else:
                        print('Error: Unknown type -', type(key_dict))
                        raise Exception('Unknown type')
                for sub_key, sub_value in value.items():
                    if sub_key == '$ref':
                        resolve_and_update_properties(sub_value, key_dict, open_api)
                        body[key] = key_dict
                    elif sub_key == 'items':
                        for item_name, item in sub_value.items():
                            if item_name == '$ref':
                                resolve_and_update_properties(item, key_dict, open_api)
                            else:
                                item_dict = {}
                                if 'type' in item:
                                    if item['type'] == 'array':
                                        item_dict = []
                                    elif item['type'] != 'object':
                                        print('Error: Unknown type -', type(item['type']))
                                        raise Exception('Unknown type')
                                if 'properties' in item:
                                    for item_prop, item_prop_value in item['properties'].items():
                                        if isinstance(item_dict, dict):
                                            item_dict[item_prop] = process_property(item_prop_value)
                                        else:
                                            item_dict.append(process_property(item_prop_value))
                                else:
                                    print('Error: something went wrong')
                                if isinstance(key_dict, dict):
                                    key_dict.update(item_dict)
                                elif isinstance(key_dict, list):
                                    key_dict.append(item_dict)
                                else:
                                    print('Error: Unknown type -', type(key_dict))
                                    raise Exception('Unknown type')
                        body[key] = key_dict
                    elif sub_key != 'type':
                        print('Error: Unknown key -', sub_key)
        if '$ref' in response['content']['application/json']['schema']:
            resolve_and_update_properties(response['content']['application/json']['schema']['$ref'], body, open_api)
        print('body: ', body)
    except Exception as e:
        print('Something went wrong:', e)
        return ''


def get_response_headers(response):
    # TODO: Add all headers
    headers = []
    if 'content' in response:
        headers.append({
            'key': 'Content-Type',
            'value': list(response['content'].keys())[0]
        })
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
    main()
