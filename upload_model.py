from huggingface_hub import HfApi
import os

api = HfApi()
api.upload_file(
    path_or_fileobj='xg_model.pkl',
    path_in_repo='xg_model.pkl',
    repo_id='TH6672/xg-calculator',
    repo_type='space',
    token=os.getenv('HF_TOKEN')
)
print('Model uploaded to Hugging Face')