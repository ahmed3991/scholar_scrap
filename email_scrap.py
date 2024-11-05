from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from tika import parser
from collections import Counter
import os
import re

def find_closest_email(emails, name):
    # Extract the names from emails (before '@')
    email_names = [re.split(r'@', email)[0] for email in emails]

    # Combine name and email names for vectorization
    texts = [name] + email_names

    # Fit TF-IDF and transform
    vectorizer = TfidfVectorizer().fit(texts)
    vectors = vectorizer.transform(texts)

    # Compute cosine similarity between name and each email name
    name_vector = vectors[0]  # the vector for the name
    email_vectors = vectors[1:]  # the vectors for the email names
    similarities = cosine_similarity(name_vector, email_vectors).flatten()

    # Get the email with the highest similarity
    most_similar_index = similarities.argmax()
    nearest_email = emails[most_similar_index]
    
    # Return the email with the highest similarity score
    return nearest_email, similarities

def get_email_statistics(emails):
    # Count occurrences of each email
    email_counts = Counter(emails)
    
    # Sort by count in descending order, keeping the original order of emails with the same frequency
    sorted_emails = sorted(email_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Get the most frequent email
    most_frequent_email = sorted_emails[0] if sorted_emails else None
    
    return most_frequent_email , sorted_emails

def extract_emails_and_names(text):
    # Regular expression to find email addresses
    email_pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
    emails = re.findall(email_pattern, text)

    # Regular expression to find author names
    # Here, we assume names appear before emails with "By" or "Authors:" keywords
    #name_pattern = r"(?:Authors?:?|By)\s*([A-Za-z ,]+)"
    #names = re.findall(name_pattern, text)

    return emails


def get_emails_from_author_id(path, author_id):
    emails_list = []

    directory_path = os.path.join(path, author_id)

    # Filter for PDF files only
    file_paths = [
        os.path.join(directory_path, filename)
        for filename in os.listdir(directory_path)
        if filename.lower().endswith('.pdf') and os.path.isfile(os.path.join(directory_path, filename))
    ]
    
    for filepath in file_paths:
        parsed_document = parser.from_file(filepath)
        text = parsed_document.get('content', '')

        emails = extract_emails_and_names(text)
        emails_list.append(emails)
    
    return [item for list in emails_list for item in list]


if __name__ == "__main__":
    user_name = "Alahyane, Mohamed"  # Specify the user name directly
    
    author_appr_name = 'Alahyane M'
    
    emails = get_emails_from_author_id('pdfs',user_name.replace(' ','_'))

    most_frequent,sorted_emails = get_email_statistics(emails)
    
    print(sorted_emails)

    closest_email,similarity_coef = find_closest_email(emails,author_appr_name)

    print(closest_email,similarity_coef)


