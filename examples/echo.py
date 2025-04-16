#!/usr/bin/env python3
"""
Echo CLI - A simple echo command line program

This application receives command line arguments and echoes them to standard output
"""

import sys
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="A simple echo command line program")
    parser.add_argument("words", nargs="*", help="Words to echo")
    parser.add_argument("--uppercase", "-u", action="store_true", help="Convert to uppercase")
    parser.add_argument("--lowercase", "-l", action="store_true", help="Convert to lowercase")
    parser.add_argument("--join", "-j", help="Join words with specified separator")
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")
    
    args = parser.parse_args()
    
    # Process words
    words = args.words if args.words else []
    
    if args.uppercase:
        words = [word.upper() for word in words]
    elif args.lowercase:
        words = [word.lower() for word in words]
    
    # Join words
    if args.join is not None:
        result = args.join.join(words)
    else:
        result = " ".join(words)
    
    # Output result
    if args.format == "json":
        output = {
            "original": args.words,
            "result": result,
            "count": len(words),
            "options": {
                "uppercase": args.uppercase,
                "lowercase": args.lowercase,
                "join": args.join,
                "format": args.format
            }
        }
        print(json.dumps(output, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main() 