import requests

test_url = 'https://drive.google.com/thumbnail?id=1ankhKK7EgcmJ_4pdssHfh3bsPLKgdupr&sz=w400'
print('Testing thumbnail URL:', test_url)

try:
    response = requests.head(test_url, timeout=10)
    print('Status:', response.status_code)
    print('Content-Type:', response.headers.get('content-type'))
    print('Success: Thumbnail URL works!')
except Exception as e:
    print('Error:', e)

# Test original URL too
original_url = 'https://drive.google.com/uc?export=view&id=1ankhKK7EgcmJ_4pdssHfh3bsPLKgdupr'
print('\nTesting original URL:', original_url)

try:
    response = requests.head(original_url, timeout=10)
    print('Status:', response.status_code)
    print('Content-Type:', response.headers.get('content-type'))
except Exception as e:
    print('Error:', e)
