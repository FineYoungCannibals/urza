from urza.config.settings import DO_TOKEN, DO_BASE_URL, DO_BUCKET_NAME
import httpx
import boto3

class DOAgent():
    def __init__(self):
        self.do_token = DO_TOKEN
        self.headers = {'Content-Type':'application/json', \
            'Authorization':f'Bearer {self.do_token}'}
    
    def test_connection(self):
        '''
        Docstring for test_connection
        @returns True, able to authenitcate to DO API using keys 
        '''
        try:
            with httpx.Client(base_url=DO_BASE_URL, headers=self.headers) as client:
                response = client.get('/spaces/keys')
                response.raise_for_status()
                data = response.json()
                return data
        except Exception as e:
            print(f"Error listing spaces: {str(e)}")
            return None

    
    def list_keys(self):
        '''
        Docstring for list_keys
        @returns True, able to authenitcate to DO API using keys 
        '''
        with httpx.Client(base_url=DO_BASE_URL, headers=self.headers) as client:
            response = client.get('/spaces/keys')
        return response.json()
    
    def create_spaces_keys(self, botname):
        '''
        @return str: do spaces keys
        '''
        payload = {
            "name": botname,
            "grants":[
                {
                    "bucket":DO_BUCKET_NAME,
                    "permission":"readwrite"
                }
            ]
        }
        with httpx.Client(base_url=DO_BASE_URL, headers=self.headers) as client:
            response = client.post('/spaces/keys', json=payload, timeout=30)
            response.raise_for_status()
        return response.json()
    
    
    def revoke_spaces_keys(self, key_name,access_key):
        '''
        Delete the old key, make a new one by the new name
        
        :param self: Description
        :param old_keys: Description
        :return new_keys
        '''
        with httpx.Client(base_url=DO_BASE_URL, headers=self.headers) as client:
            response = client.delete(f'/spaces/keys/{access_key}', timeout=30)
            response.raise_for_status()
            if int(response.status_code) == 204:
                print('Cycling Access Key')
            data = self.create_spaces_keys(key_name)

        return data