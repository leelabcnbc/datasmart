import json

def load_file(savepath, load_json=True):
    """just created to have higher GPA in code climate"""
    with open(savepath, 'rt', encoding='utf-8') as f:
        content_back = f.read()
        if load_json:
            return json.loads(content_back)
        else:
            return content_back

def save_file(savepath, content):
    """just created to have higher GPA in code climate"""
    with open(savepath, 'wt', encoding='utf-8') as f:
        f.write(content)