import time
import socket
import requests


class HockeyRESTAPI:

    def __init__(self, max_request_retries=5):
        self.auth_file = None  # os.path.expanduser(auth_file)
        self.config_file = None  # os.path.expanduser(config_file)
        self.mode = None
        self.token = None
        self._credentials = None
        self.cookie = None
        self._session = requests.Session()
        self._config = dict()  # configparser.ConfigParser()
        self._config['retries'] = int(max_request_retries)
        self._config['protocol'] = 'http'
        self._config['host'] = 'ec2-3-15-171-155.us-east-2.compute.amazonaws.com/'
        self._config['timeout'] = 35
        self._netrc = None  # netrc.netrc(self.auth_file)

    def _get_config(self, key):
        return self._config.get(key)

    def _setup_url(self, parts, version=None):
        protocol = self._get_config('protocol')
        host = self._get_config('host')
        url = '/'.join([f'{k}' for k in parts])
        # vers = version if version is not None else self._get_config('version')
        return requests.utils.requote_uri(f'{protocol}://{host}/api/{url}.php')

    def _do_request(self, rq_method, url_parts, params=None, data=None, json=None, version=None, stream=False):
        url = self._setup_url(url_parts, version)
        params_rq = {'api_key': 'None' if self.token is None else self.token['apiKey']}

        # params = self._add_virtual_params(params)

        if params is not None:
            params_rq.update(params)

        prep_rq = self._session.prepare_request(requests.Request(rq_method,
                                                                 url,
                                                                 params=params_rq,
                                                                 data=data,
                                                                 json=json,
                                                                 cookies=self.cookie))
        content = self._session.send(prep_rq,
                                     timeout=int(self._get_config('timeout')),
                                     stream=stream)
        self.last_url = prep_rq.url  # save last url
        if content.status_code in [200, 201]:
            self.cookie = content.cookies
            return content
        elif content.status_code == requests.codes.not_found:
            time.sleep(5)
        else:
            content.raise_for_status()
        return None

    def request(self, rq_method, url_parts, params=None, data=None, json=None, version=None, stream=False):
        """
        Perform a request on a restapi endpoint
        """
        response = None
        # if self.token is None:
        #     self._login()

        for _ in range(int(self._get_config('retries'))):
            try:
                response = self._do_request(rq_method, url_parts, params=params, data=data, json=json, version=version,
                                            stream=stream)
            except requests.exceptions.HTTPError as exp:
                if str(exp).startswith('404 Client Error'):
                    print(f'HockeyRESTAPI Error Encountered: {str(exp)}')
                    break
                else:
                    if bool(self._get_config('ignore_errors')) is False:
                        raise RuntimeError(exp.response.text)
            except requests.exceptions.ReadTimeout as rte:
                if bool(self._get_config('ignore_errors')) is False:
                    raise rte
            except socket.timeout as rte:
                if bool(self._get_config('ignore_errors')) is False:
                    raise rte
            except Exception as exp:
                print(f'HockeyRESTAPI Unmanaged Exception: {exp}')
                raise exp
            else:
                try:
                    response = response.json()
                except BaseException:
                    pass

                break
        return response


class HockeyAPI(HockeyRESTAPI):

    def create_player(self, player_json):
        """
        Method to create a new player in the database
        :param player_json: a dictionary of the form:

        :return: response from the server
        """
        return self.request('post', ['players', 'create_player'], json=player_json)

    def get_leagues(self):
        """
        Method to retrieve all the leagues in the database

        :return: json result of query
        """
        return self.request('get', ['leagues', 'read'])

    def get_players(self):
        """
        Method to retrieve all the players in the database

        :return: json result of query
        """
        return self.request('get', ['players', 'read'])