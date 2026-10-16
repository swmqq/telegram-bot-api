import requests
# игнорируем предупреждение, что сертификата нет не защищен, только для локальной разработки!!!!!!!! 
from requests.packages import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

data = requests.get('https://localhost:7003/authors/4', verify=False).json()

print(data["books"])