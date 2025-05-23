import os
import re
import hashlib
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Utility Functions (Copied from Docs2saurus/d2c2.py)

def generate_unique_id(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def escape_title(title):
    if '"' in title:
        title = title.replace('"', '\\"')
    return f'title: "{title}"\n'

def sanitize_and_clean_name(name, max_length=20):
    """
    Strips list indicators, sanitizes, and truncates the name to ensure it is within the maximum length.

    Args:
        name (str): The name to be sanitized and cleaned.
        max_length (int): The maximum length for the cleaned name.
    """
    # Combine regex operations to remove periods, invalid characters, preserve double asterisks
    name = re.sub(r'^[\.\-]+\s*|[<>:"/\\|?()]', '', name).strip()
    name = name.replace('.', '_')
    # Remove trailing spaces
    name = name.rstrip()

    # Truncate the name if it exceeds the maximum length
    base, ext = os.path.splitext(name)
    if len(base) > max_length:
        base = base[:max_length//2] + '...' + base[-max_length//2:]

    # Disallow invalid folder characters like . or space in the last 5 characters
    if len(base) > 5:
        base = base[:-5] + re.sub(r'[ ._]', '', base[-5:])
    else:
        base = re.sub(r'[ .]', '', base)

    base = base.replace('.', '')
    return base + ext

def alternative_sanitize_and_clean_name(name, max_length=20):
    """
    Alternative sanitization function that removes numbers and replaces periods with underscores.
removes digits#######################also uses unsndersocres?
    Args:
        name (str): The name to be sanitized and cleaned.
        max_length (int): The maximum length for the cleaned name.
    """
    # Remove invalid characters and replace periods and numbers
    name = re.sub(r'[<>:"/\\|?]', '', name)  # Remove invalid characters
    name = re.sub(r'\.', '', name)  # Replace periods with nothing
    name = re.sub(r'^\d+', '', name)  # Remove digits only if they appear as the first character in a line


       # Remove trailing spaces
    name = name.rstrip()

    # Truncate the name if it exceeds the maximum length
    base, ext = os.path.splitext(name)
    if len(base) > max_length:
        base = base[:max_length//2] + '...' + base[-max_length//2:]

    # Disallow invalid folder characters like . or space in the last 5 characters
    if len(base) > 5:
        base = base[:-5] + re.sub(r'[ ._]', '', base[-5:])
    else:
        base = re.sub(r'[ .]', '', base)

    base = base.replace('.', '')
    return base + ext

def write_md_file(path, content, lines, front_matter=None):
    """
    Writes content and front matter to a Markdown file.

    Args:
        path (str): The path to the Markdown file.
        content (str): The main content to write.
        lines (list): Additional content lines to write.
        front_matter (str, optional): The front matter to include at the top of the file.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)  # Ensure parent directories exist
    with open(path, 'w', encoding='utf-8') as md_file:
        # Write the front matter if provided
        if front_matter:
            #md_file.write('---\n')  # Start of front matter
            md_file.write(front_matter)  # Write the front matter content
            #md_file.write('---\n\n')  # End of front matter and add a blank line

        # Write the main content
        md_file.write(content + '\n')

        # Write additional content lines
        for line in lines:
            # Remove '**' markers from the line
            cleaned_line = line.replace('**', '')
            # Write the cleaned line to the file
            md_file.write(cleaned_line + '\n')

def categorize_lines(list_content):
    """
    Categorizes lines from the list content into a hierarchical structure.

    Args:
        list_content (list): The list of lines to categorize.

    Returns:
        dict: The hierarchical structure of categorized lines.
    """
    stack = []
    root = {'Children': [], 'BodyLines': [], 'UniqueID': 'root'}

    for line_number, line in enumerate(list_content, 1):
        # Preserve original line for body lines
        original_line = line.rstrip()
        # Sanitize and clean the line for structure determination
        line_content = sanitize_and_clean_name(line)
        indent_level = len(line) - len(line.lstrip())
        content = line_content.strip()

        if not content:
            continue  # Skip empty lines

        is_body_line = '**' in original_line

        if is_body_line:
            parent_node = stack[-1]
            parent_node.setdefault('BodyLines', []).append(original_line)
            continue

        unique_id = generate_unique_id(f"{indent_level}_{content}_{line_number}")
        node = {
            'IndentLevel': indent_level,
            'Content': content,
            'Children': [],
            'BodyLines': [],
            'UniqueID': unique_id,
            'FULLLINE': line
        }

        while stack and stack[-1]['IndentLevel'] >= indent_level:
            stack.pop()

        if stack:
            parent_node = stack[-1]
            parent_node['Children'].append(node)
        else:
            root['Children'].append(node)

        stack.append(node)

    return root

# Structure Creation Function (Copied from Docs2saurus/d2c2.py)
def create_structure(node, parent_path, id_to_path_map, sanitize_function, allow_empty_folders):
    """
    Recursively creates directories and Markdown files based on the hierarchical structure.

    Args:
        node (dict): The current node in the hierarchical structure.
        parent_path (str): The path to the parent directory.
        id_to_path_map (dict): A mapping from unique IDs to paths.
        sanitize_function (function): The function to use for sanitizing names.
        allow_empty_folders (bool): Whether to allow empty folders.
    """
    for child in node.get('Children', []):
        content = child['Content']
        content_FULLLINE = child['FULLLINE']
        sanitized_name = sanitize_function(content)
        current_path = os.path.join(parent_path, sanitized_name)

        # Normalize paths to ensure consistent comparison
        normalized_parent_path = os.path.normpath(parent_path)
        normalized_current_path = os.path.normpath(current_path)

        # Ensure the path is within the intended directory
        if not os.path.commonpath([normalized_current_path, normalized_parent_path]) == normalized_parent_path:
            raise ValueError(f"Invalid path detected: {normalized_current_path} is not within {normalized_parent_path}")

        # Handle name conflicts by appending a unique identifier
        if os.path.exists(normalized_current_path):
            sanitized_name += '_' + child['UniqueID'][:6]
            normalized_current_path = os.path.join(normalized_parent_path, sanitized_name)

        # Store the mapping from unique ID to path
        id_to_path_map[child['UniqueID']] = normalized_current_path

        # Prepare the front matter with proper escaping
        title_line = escape_title(content_FULLLINE)
        front_matter = f"---\n{title_line}---\n\n"

        if child['Children']:
            # Create a directory for nodes with children
            os.makedirs(normalized_current_path, exist_ok=True)
            # Create an index.md file for the directory
            md_file_path = os.path.join(normalized_current_path, 'index.md')
            write_md_file(md_file_path, '', child.get('BodyLines', []), front_matter)
            # Recursively create structure for child nodes
            create_structure(child, normalized_current_path, id_to_path_map, sanitize_function, allow_empty_folders)
        elif allow_empty_folders:
            # Check if any siblings have children
            siblings_have_children = any(sibling['Children'] for sibling in node['Children'] if sibling != child)

            if siblings_have_children:
                # Create a directory with index.md if any siblings have children
                os.makedirs(normalized_current_path, exist_ok=True)
                md_file_path = os.path.join(normalized_current_path, 'index.md')
                write_md_file(md_file_path, '', child.get('BodyLines', []), front_matter)
        else:
                # Create a .md file if no siblings have children
                md_file_path = f"{normalized_current_path}.md"
                write_md_file(md_file_path, '', child.get('BodyLines', []), front_matter)


def main():
    parser = argparse.ArgumentParser(description='Process a Markdown list into a structured directory of Markdown files.')
    parser.add_argument('input_file', help='Path to the input Markdown file.')
    parser.add_argument('output_dir', help='Path to the output base directory.')
    parser.add_argument('--remove-digits', action='store_true', help='Use alternative sanitization to remove digits.')
    parser.add_argument('--allow-empty-folders', action='store_true', help='Allow the creation of empty folders.')

    args = parser.parse_args()

    input_file = args.input_file
    base_dir = args.output_dir
    use_alternative_sanitization = args.remove_digits
    allow_empty_folders = args.allow_empty_folders

    try:
        logging.info("Starting processing...")
        os.makedirs(base_dir, exist_ok=True)

        # Read the input file content directly
        with open(input_file, 'r', encoding='utf-8') as f:
            list_content = [line.rstrip() for line in f]

        # Build the hierarchy tree
        root = categorize_lines(list_content)

        # Mapping from unique IDs to filesystem paths
        id_to_path_map = {'root': base_dir}

        # Select the sanitization function based on the argument
        if use_alternative_sanitization:
            sanitize_function = alternative_sanitize_and_clean_name
        else:
            sanitize_function = sanitize_and_clean_name

        # Create the folder structure and .md files using the selected sanitization function
        create_structure(root, base_dir, id_to_path_map, sanitize_function, allow_empty_folders)

        logging.info("Processing completed successfully!")

    except FileNotFoundError:
        logging.error(f"Error: Input file not found at {input_file}")
    except Exception as e:
        logging.error(f"An error occurred during processing: {str(e)}")

if __name__ == "__main__":
    main()