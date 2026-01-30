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
            print(response.json())
        return response.json()
    
    def create_spaces_keys(self):
        '''
        @return str: do spaces keys
        '''
        grants = [
            {
                "bucket":DO_
            }
        ]
        with httpx.Client(base_url=DO_BASE_URL, headers=self.headers) as client:
            response = client.post('/spaces/keys')
            print(response.json())
        return
    
    
    def revoke_spaces_keys(self, old_keys):
        '''
        Docstring for revoke_spaces_keys
        
        :param self: Description
        :param old_keys: Description
        :return new_keys
        '''
        print("TODO")
        return