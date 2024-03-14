"""
Script to get the DOI prefixes of all the preprint servers accessible from Crossref API.
The populate_doi_institution_register() function creates a register of DOI prefixes by using the Crossref API and
searching all works having a value for the property 'is-preprint-of' (via get_crossref_results() function).
For some prefixes it is possible to get the institution name from the results of this API call; the DOI prefixes for
which no institution name is specified in the publication's metadata are set to an empty string and later filled with a
second API call (via enhance_doi_institution_register() function).
"""

from urllib.parse import quote
import requests
from tqdm import tqdm
import json
from collections import defaultdict


def get_crossref_results(nrows=1000):
    cursor = '*'
    url = f"https://api.crossref.org/works?filter=relation.type:is-preprint-of&rows={nrows}&cursor={cursor}"

    response = requests.get(url, headers={'User-Agent': input('Enter User-Agent: '), 'mailto': input('Enter email: ')})
    data = response.json()

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return None
    else:
        total_results = data.get('message', {}).get('total-results')
        print(f"Total results: {total_results}")
        items = data.get('message', {}).get('items', [])
        next_cursor = quote(data.get('message', {}).get('next-cursor'))
        # Process the current page of results
        for item in items:
            yield item
        while len(items) == nrows:
            # Get the next page of results
            response = requests.get(f"https://api.crossref.org/works?filter=relation.type:is-preprint-of&rows={nrows}&cursor={next_cursor}")
            data = response.json()
            items = data.get('message', {}).get('items', [])
            # Process the current page of results
            for item in items:
                yield item
        else:
            return None


def extract_doi_prefix(doi):
    # Extract DOI prefix (e.g., "10.1234" from "10.1234/journal.article123")
    return doi.split("/")[0]


def populate_doi_institution_register(out_filepath:str):

    result = defaultdict(set)

    for i in tqdm(get_crossref_results()):
        doi = i.get("DOI", "")
        institution = i.get("institution", "")

        if doi:
            doi_prefix = extract_doi_prefix(doi)
            result[doi_prefix].add(institution[0].get("name", "")) if institution else result[doi_prefix].add("")

    result = dict(result)
    for k,v in result.items():
        if isinstance(v, set):
            result[k] = list(v)

    with open(out_filepath, 'w') as f:
        json.dump(result, f, indent=4)

    return result


def enhance_doi_institution_register(input_register_path, output_register_path):
    output = {}
    with open(input_register_path, 'r') as f:
        data = json.load(f)
    for k,v in tqdm(data.items()):
        request = requests.get(f"https://api.crossref.org/prefixes/{k}")
        if request.status_code == 200:
            name = request.json().get("message", {}).get("name", "")
            v.append(name) if (name not in v and name) else v
            # v = [i for i in v if i != ""]
            output[k] = v
        else:
            output[k] = [i for i in v if i != ""]

    print(output)

    with open(output_register_path, 'w') as f:
        json.dump(output, f, indent=4)
        return output


if __name__ == "__main__":
    tmp_register_path = "data/tmp_register.json"
    doi_institution_register = "data/doi_institution_register.json"
    populate_doi_institution_register(tmp_register_path)
    enhance_doi_institution_register(tmp_register_path, doi_institution_register)
