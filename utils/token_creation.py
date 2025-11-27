from tgtg import TgtgClient

client = TgtgClient(email="zhaoshiyao2015@gmail.com")
credentials = client.get_credentials()

print(credentials)