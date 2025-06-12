#!/usr/bin/env python3

import argparse
from routes import handle_git_query

def main():
    parser = argparse.ArgumentParser(description="Git Agent - AI-powered Git assistant")
    parser.add_argument("query", nargs="*", help="Your query for the Git agent")
    args = parser.parse_args()
    
    # Get the query from arguments or prompt the user
    if args.query:
        query = " ".join(args.query)
    else:
        query = input("What would you like to do with your Git repository? ")
    
    # Process the query
    response = handle_git_query(query)
    
    print("\nGitAgent Response:")
    print(response)

if __name__ == "__main__":
    main()
