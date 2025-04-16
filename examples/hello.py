#!/usr/bin/env python3
"""
Hello World - A simple example application

This application demonstrates how to use command line arguments and output results
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="A simple example application")
    parser.add_argument("--name", "-n", default="World", help="Name to greet")
    parser.add_argument("--language", "-l", default="en", choices=["cn", "en"], help="Output language (cn or en)")
    parser.add_argument("--repeat", "-r", type=int, default=1, help="Number of repetitions")
    
    args = parser.parse_args()
    
    greeting = "你好" if args.language == "cn" else "Hello"
    message = f"{greeting}, {args.name}!"
    
    for i in range(args.repeat):
        print(message)


if __name__ == "__main__":
    main() 