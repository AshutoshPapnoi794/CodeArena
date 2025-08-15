import requests
import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

API_ALL = "https://leetcode.com/api/problems/all/"
API_GRAPHQL = "https://leetcode.com/graphql"

# GraphQL query for detailed info (with total submissions)
QUERY = """
query getQuestionDetails($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    topicTags { name }
    categoryTitle
    likes
    dislikes
    stats
    similarQuestions
  }
}
"""

def fetch_all_problems():
    """Fetch all problem metadata from REST API."""
    resp = requests.get(API_ALL)
    resp.raise_for_status()
    return resp.json().get("stat_status_pairs", [])

def fetch_graphql_details(slug):
    """Fetch problem details from GraphQL API."""
    try:
        resp = requests.post(
            API_GRAPHQL,
            json={"query": QUERY, "variables": {"titleSlug": slug}},
            timeout=10
        )
        resp.raise_for_status()
        q = resp.json()["data"]["question"]

        topics = [t["name"] for t in q.get("topicTags", [])]
        category = q.get("categoryTitle", "")
        likes = q.get("likes", 0)
        dislikes = q.get("dislikes", 0)
        stats_json = json.loads(q.get("stats", "{}"))
        total_submissions = stats_json.get("totalSubmission", 0)
        total_accepted = stats_json.get("totalAccepted", 0)
        similar = q.get("similarQuestions", "")

        return topics, category, likes, dislikes, total_submissions, total_accepted, similar
    except Exception:
        return [], "", 0, 0, 0, 0, ""

def save_to_csv(problems, filename="leetcode_with_submissions.csv"):
    """Save combined problem data to CSV."""
    with open(filename, mode="w", newline='', encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([
            "ID", "Title", "Difficulty", "Link", "Topics", "Acceptance Rate (%)",
            "Premium Only", "Category", "Likes", "Dislikes", "Total Submissions",
            "Total Accepted", "Similar Questions"
        ])
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_problem = {
                executor.submit(fetch_graphql_details, item["stat"]["question__title_slug"]): item
                for item in problems
            }
            for future in as_completed(future_to_problem):
                item = future_to_problem[future]
                stat = item["stat"]
                q_id = stat["frontend_question_id"]
                title = stat["question__title"]
                slug = stat["question__title_slug"]
                link = f"https://leetcode.com/problems/{slug}/"
                difficulty = {1: "Easy", 2: "Medium", 3: "Hard"}.get(item["difficulty"]["level"], "Unknown")
                acceptance = round(stat.get("total_acs", 0) / stat.get("total_submitted", 1) * 100, 2)
                premium = item.get("paid_only", False)
                
                topics, category, likes, dislikes, total_sub, total_acc, similar = future.result()
                writer.writerow([
                    q_id, title, difficulty, link, ", ".join(topics), acceptance,
                    premium, category, likes, dislikes, total_sub, total_acc, similar
                ])

def main():
    problems = fetch_all_problems()
    save_to_csv(problems)

if __name__ == "__main__":
    main()
