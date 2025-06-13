#!/usr/bin/env python3
import os
import re
import argparse
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import sys
import html

@dataclass
class ProtoField:
    """Represents a field in a protobuf message"""
    name: str
    type: str
    number: int
    label: str = ""  # optional, required, repeated
    comment: str = ""
    default_value: str = ""
    is_deprecated: bool = False

@dataclass
class ProtoMessage:
    """Represents a protobuf message"""
    name: str
    fields: List[ProtoField] = field(default_factory=list)
    comment: str = ""
    nested_messages: List['ProtoMessage'] = field(default_factory=list)
    enums: List['ProtoEnum'] = field(default_factory=list)

@dataclass
class ProtoEnum:
    """Represents a protobuf enum"""
    name: str
    values: Dict[str, int] = field(default_factory=dict)
    comment: str = ""

@dataclass
class ProtoMethod:
    """Represents a protobuf service method"""
    name: str
    input_type: str
    output_type: str
    comment: str = ""
    http_method: str = ""
    http_path: str = ""
    http_body: str = ""

@dataclass
class ProtoService:
    """Represents a protobuf service"""
    name: str
    methods: List[ProtoMethod] = field(default_factory=list)
    comment: str = ""

class ProtoParser:
    """Parser for protobuf files"""
    
    def __init__(self):
        self.messages: Dict[str, ProtoMessage] = {}
        self.services: Dict[str, ProtoService] = {}
        self.enums: Dict[str, ProtoEnum] = {}
        self.packages: Dict[str, str] = {}  # Map file paths to package names
        self.imports: Dict[str, List[str]] = {}  # Track imports per file
        
    def parse_file(self, filepath: str) -> None:
        """Parse a single protobuf file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract package name
        package_match = re.search(r'package\s+([\w.]+);', content)
        if package_match:
            self.packages[filepath] = package_match.group(1)
        
        # Extract imports
        import_matches = re.findall(r'import\s+"([^"]+)";', content)
        if import_matches:
            self.imports[filepath] = import_matches
        
        # Remove C-style comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
        
        # Parse services
        self._parse_services(content, filepath)
        
        # Parse messages
        self._parse_messages(content, filepath)
        
        # Parse enums
        self._parse_enums(content, filepath)
    
    def parse_repository(self, repo_root: str) -> None:
        """Parse all proto files in a repository"""
        for root, dirs, files in os.walk(repo_root):
            for file in files:
                if file.endswith('.proto'):
                    filepath = os.path.join(root, file)
                    try:
                        self.parse_file(filepath)
                    except Exception as e:
                        print(f"Warning: Failed to parse {filepath}: {e}")
        
        # Add well-known Google protobuf types
        self._add_well_known_types()
        
        # Build qualified type names after parsing all files
        self._build_qualified_names()
    
    def _add_well_known_types(self) -> None:
        """Add well-known Google protobuf types"""
        # Add Timestamp type
        timestamp_msg = ProtoMessage(name="Timestamp")
        timestamp_msg.comment = "A Timestamp represents a point in time independent of any time zone or local calendar, encoded as a count of seconds and fractions of seconds at nanosecond resolution."
        timestamp_msg.fields = [
            ProtoField(name="seconds", type="int64", number=1, comment="Represents seconds of UTC time since Unix epoch 1970-01-01T00:00:00Z."),
            ProtoField(name="nanos", type="int32", number=2, comment="Non-negative fractions of a second at nanosecond resolution.")
        ]
        timestamp_msg._source_file = "google/protobuf/timestamp.proto"
        self.messages["Timestamp"] = timestamp_msg
        self.messages["google.protobuf.Timestamp"] = timestamp_msg
        self.packages["google/protobuf/timestamp.proto"] = "google.protobuf"
        
        # Add Duration type
        duration_msg = ProtoMessage(name="Duration")
        duration_msg.comment = "A Duration represents a signed, fixed-length span of time represented as a count of seconds and fractions of seconds at nanosecond resolution."
        duration_msg.fields = [
            ProtoField(name="seconds", type="int64", number=1, comment="Signed seconds of the span of time."),
            ProtoField(name="nanos", type="int32", number=2, comment="Signed fractions of a second at nanosecond resolution of the span of time.")
        ]
        duration_msg._source_file = "google/protobuf/duration.proto"
        self.messages["Duration"] = duration_msg
        self.messages["google.protobuf.Duration"] = duration_msg
        self.packages["google/protobuf/duration.proto"] = "google.protobuf"
        
        # Add Any type
        any_msg = ProtoMessage(name="Any")
        any_msg.comment = "Any contains an arbitrary serialized protocol buffer message along with a URL that describes the type of the serialized message."
        any_msg.fields = [
            ProtoField(name="type_url", type="string", number=1, comment="A URL/resource name that uniquely identifies the type of the serialized protocol buffer message."),
            ProtoField(name="value", type="bytes", number=2, comment="Must be a valid serialized protocol buffer of the above specified type.")
        ]
        any_msg._source_file = "google/protobuf/any.proto"
        self.messages["Any"] = any_msg
        self.messages["google.protobuf.Any"] = any_msg
        self.packages["google/protobuf/any.proto"] = "google.protobuf"
        
        # Add Payload type
        payload_msg = ProtoMessage(name="Payload")
        payload_msg.comment = "Payload is used to serialize/deserialize data that is passed to/from activity/workflow implementations that are language agnostic."
        payload_msg.fields = [
            ProtoField(name="metadata", type="map<string,bytes>", number=1, comment="Metadata contains additional context information for this payload."),
            ProtoField(name="data", type="bytes", number=2, comment="Serialized data.")
        ]
        payload_msg._source_file = "temporal/api/common/v1/message.proto"
        self.messages["Payload"] = payload_msg
        self.messages["temporal.api.common.v1.Payload"] = payload_msg
        self.packages["temporal/api/common/v1/message.proto"] = "temporal.api.common.v1"
    
    def _build_qualified_names(self) -> None:
        """Build qualified names for all types based on package information"""
        qualified_messages = {}
        qualified_enums = {}
        
        for filepath, package in self.packages.items():
            # Find messages and enums from this file and add package prefix
            for msg_name, msg in list(self.messages.items()):
                if hasattr(msg, '_source_file') and msg._source_file == filepath:
                    qualified_name = f"{package}.{msg_name}"
                    qualified_messages[qualified_name] = msg
                    # Keep both qualified and unqualified for backwards compatibility
                    qualified_messages[msg_name] = msg
            
            for enum_name, enum in list(self.enums.items()):
                if hasattr(enum, '_source_file') and enum._source_file == filepath:
                    qualified_name = f"{package}.{enum_name}"
                    qualified_enums[qualified_name] = enum
                    qualified_enums[enum_name] = enum
        
        # Update the dictionaries with qualified names
        self.messages.update(qualified_messages)
        self.enums.update(qualified_enums)
    
    def _find_matching_brace(self, content: str, start_pos: int) -> int:
        """Find the matching closing brace for an opening brace at start_pos"""
        brace_count = 0
        for i, char in enumerate(content[start_pos:], start_pos):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return i
        return -1  # No matching brace found
    
    def _parse_services(self, content: str, filepath: str) -> None:
        """Parse service definitions from protobuf content"""
        # Find service definitions with proper brace matching
        service_start_pattern = r'service\s+(\w+)\s*\{'
        
        for start_match in re.finditer(service_start_pattern, content):
            service_name = start_match.group(1)
            start_pos = start_match.end() - 1  # Position of the opening brace
            
            # Find the matching closing brace
            end_pos = self._find_matching_brace(content, start_pos)
            if end_pos == -1:
                continue  # Malformed service block
            
            service_body = content[start_pos + 1:end_pos]
            service = ProtoService(name=service_name)
            service._source_file = filepath  # Track source file
            
            # Parse RPC methods with proper nested brace handling
            rpc_start_pattern = r'rpc\s+(\w+)\s*\((\w+)\)\s*returns\s*\((\w+)\)\s*\{'
            
            for rpc_start_match in re.finditer(rpc_start_pattern, service_body):
                method_name = rpc_start_match.group(1)
                input_type = rpc_start_match.group(2)
                output_type = rpc_start_match.group(3)
                rpc_start_pos = rpc_start_match.end() - 1  # Position of the opening brace
                
                # Find the matching closing brace for this RPC method
                rpc_end_pos = self._find_matching_brace(service_body, rpc_start_pos)
                if rpc_end_pos == -1:
                    continue  # Malformed RPC block
                
                method_body = service_body[rpc_start_pos + 1:rpc_end_pos]
                
                method = ProtoMethod(
                    name=method_name,
                    input_type=input_type,
                    output_type=output_type
                )
                
                # Parse HTTP annotations with nested brace handling
                http_start_pattern = r'option\s+\(google\.api\.http\)\s*=\s*\{'
                http_start_match = re.search(http_start_pattern, method_body)
                
                if http_start_match:
                    http_start_pos = http_start_match.end() - 1  # Position of the opening brace
                    http_end_pos = self._find_matching_brace(method_body, http_start_pos)
                    
                    if http_end_pos != -1:
                        http_options = method_body[http_start_pos + 1:http_end_pos]
                        
                        # Extract HTTP method and path
                        for http_method in ['get', 'post', 'put', 'delete', 'patch']:
                            method_pattern = f'{http_method}:\\s*"([^"]+)"'
                            method_match = re.search(method_pattern, http_options)
                            if method_match:
                                method.http_method = http_method.upper()
                                method.http_path = method_match.group(1)
                                break
                        
                        # Extract body
                        body_pattern = r'body:\\s*"([^"]*)"'
                        body_match = re.search(body_pattern, http_options)
                        if body_match:
                            method.http_body = body_match.group(1)
                
                service.methods.append(method)
            
            self.services[service_name] = service
    
    def _parse_messages(self, content: str, filepath: str) -> None:
        """Parse message definitions from protobuf content"""
        message_pattern = r'message\s+(\w+)\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
        
        for match in re.finditer(message_pattern, content, re.MULTILINE | re.DOTALL):
            message_name = match.group(1)
            message_body = match.group(2)
            
            message = ProtoMessage(name=message_name)
            message._source_file = filepath  # Track source file
            
            # Parse fields
            field_pattern = r'(?:(repeated|optional|required)\s+)?(\w+(?:\.\w+)*)\s+(\w+)\s*=\s*(\d+)(?:\s*\[([^\]]*)\])?(?:\s*;//?\s*(.*))?'
            
            for field_match in re.finditer(field_pattern, message_body, re.MULTILINE):
                label = field_match.group(1) or ""
                field_type = field_match.group(2)
                field_name = field_match.group(3)
                field_number = int(field_match.group(4))
                field_options = field_match.group(5) or ""
                field_comment = field_match.group(6) or ""
                
                is_deprecated = 'deprecated = true' in field_options.lower()
                
                field = ProtoField(
                    name=field_name,
                    type=field_type,
                    number=field_number,
                    label=label,
                    comment=field_comment.strip(),
                    is_deprecated=is_deprecated
                )
                
                message.fields.append(field)
            
            self.messages[message_name] = message
    
    def _parse_enums(self, content: str, filepath: str) -> None:
        """Parse enum definitions from protobuf content"""
        enum_pattern = r'enum\s+(\w+)\s*\{([^}]+)\}'
        
        for match in re.finditer(enum_pattern, content, re.MULTILINE | re.DOTALL):
            enum_name = match.group(1)
            enum_body = match.group(2)
            
            enum = ProtoEnum(name=enum_name)
            enum._source_file = filepath  # Track source file
            
            # Parse enum values
            value_pattern = r'(\w+)\s*=\s*(\d+)(?:\s*;//?\s*(.*))?'
            
            for value_match in re.finditer(value_pattern, enum_body, re.MULTILINE):
                value_name = value_match.group(1)
                value_number = int(value_match.group(2))
                value_comment = value_match.group(3) or ""
                
                enum.values[value_name] = value_number
            
            self.enums[enum_name] = enum

class HTMLDocumentationGenerator:
    """Generates HTML API documentation from parsed protobuf definitions"""
    
    def __init__(self, parser: ProtoParser):
        self.parser = parser
        self.template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self._referenced_types_cache = None
    
    def _load_template(self, template_name: str) -> str:
        """Load a template file from the templates directory"""
        template_path = os.path.join(self.template_dir, template_name)
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: Template {template_name} not found, using fallback")
            return self._get_fallback_template(template_name)
    
    def _get_fallback_template(self, template_name: str) -> str:
        """Provide fallback templates if files are missing"""
        if template_name == 'html_head.html':
            return '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{title}</title></head><body><div class="container">'
        elif template_name == 'html_footer.html':
            return '</div><script>{javascript}</script></body></html>'
        elif template_name == 'scripts.js':
            return '// Fallback JavaScript'
        return ''
    
    def generate_html(self) -> str:
        """Generate HTML documentation"""
        doc = []
        
        # Load templates
        html_head = self._load_template('html_head.html')
        html_footer = self._load_template('html_footer.html')
        javascript = self._load_template('scripts.js')
        
        # HTML head with title
        doc.append(html_head.format(title="Temporal Cloud Ops API Reference"))
        
        # Navigation sidebar
        doc.append(self._generate_sidebar())
        
        # Main content area
        doc.append('<main class="main-content">')
        
        # Title and introduction
        doc.append('<div class="content-section">')
        doc.append('<h1>Temporal Cloud Ops API Reference</h1>')
        doc.append('</div>')
        
        # Generate documentation for each service
        for service_name, service in self.parser.services.items():
            doc.extend(self._generate_html_service_docs(service))
        
        # Generate types section
        doc.extend(self._generate_types_section())
        
        # HTML footer with JavaScript
        doc.append(html_footer.format(javascript=javascript))
        
        return "\n".join(doc)
    def _generate_sidebar(self) -> str:
        """Generate navigation sidebar"""
        nav = ['<nav class="sidebar">']
        nav.append('<div class="sidebar-content">')
        nav.append('<div class="search-container">')
        nav.append('<input type="text" class="search-input" id="searchInput" placeholder="Search services and types...">')
        nav.append('<div class="search-results" id="searchResults"></div>')
        nav.append('</div>')
        nav.append('<h2>Services</h2>')
        nav.append('<ul class="nav-list">')
        
        for service_name, service in self.parser.services.items():
            nav.append(f'<li class="nav-item">')
            nav.append(f'<a href="#{service_name.lower()}" class="nav-link">{service_name}</a>')
            nav.append('<ul class="nav-sublist">')
            
            for method in service.methods:
                nav.append(f'<li>')
                nav.append(f'<a href="#{method.name.lower()}" class="nav-sublink">{method.name}</a>')
                nav.append('</li>')
            
            nav.append('</ul>')
            nav.append('</li>')
        
        nav.append('</ul>')
        
        # Add Types section to navigation
        referenced_types = self._collect_referenced_types()
        if referenced_types:
            nav.append('<h2>Types</h2>')
            nav.append('<ul class="nav-list">')
            
            # Create a flat list of all types, sorted alphabetically with deduplication
            all_types = []
            seen_simple_names = set()
            
            for type_name, (type_obj, package) in referenced_types.items():
                simple_name = type_name.split('.')[-1]
                # Only add if we haven't seen this simple name before
                if simple_name not in seen_simple_names:
                    all_types.append((simple_name, type_name, type_obj, package))
                    seen_simple_names.add(simple_name)
            
            # Sort by simple name
            all_types.sort(key=lambda x: x[0])
            
            # Add all types in alphabetical order
            for simple_name, type_name, type_obj, package in all_types:
                nav.append(f'<li>')
                nav.append(f'<a href="#ref-{simple_name.lower()}" class="nav-sublink">{simple_name}</a>')
                nav.append('</li>')
            
            nav.append('</ul>')
        
        nav.append('</div>')
        nav.append('</nav>')
        
        return "\n".join(nav)
    

    
    def _generate_html_service_docs(self, service: ProtoService) -> List[str]:
        """Generate HTML documentation for a single service"""
        doc = []
        
        doc.append('<div class="content-section">')
        doc.append(f'<h2 id="{service.name.lower()}">{html.escape(service.name)}</h2>')
        
        if service.comment:
            doc.append(f'<p>{html.escape(service.comment)}</p>')
        
        # Generate documentation for each method
        for method in service.methods:
            doc.extend(self._generate_html_method_docs(method, service))
        
        doc.append('</div>')
        
        return doc
    
    def _generate_html_method_docs(self, method: ProtoMethod, service: ProtoService) -> List[str]:
        """Generate HTML documentation for a single method"""
        doc = []
        
        # Method name with link button
        method_anchor = method.name.lower()
        doc.append('<div class="method-header">')
        doc.append(f'<h3 id="{method_anchor}">{html.escape(method.name)}</h3>')
        doc.append(f'<button class="link-button" data-anchor="{method_anchor}" title="Copy link to this method">#</button>')
        doc.append('</div>')
        
        # Add package information
        service_package = self._get_service_package(service)
        if service_package:
            doc.append(f'<p><em>From package:</em> <code>{service_package}</code></p>')
        
        if method.comment:
            doc.append(f'<p>{html.escape(method.comment)}</p>')
        
        # HTTP method and endpoint
        if method.http_method and method.http_path:
            doc.append('<div class="method-endpoint">')
            doc.append(f'<code>{html.escape(method.http_method)} {html.escape(method.http_path)}</code>')
            doc.append('</div>')
        
        # Request format
        input_message = self.parser.messages.get(method.input_type)
        if input_message:
            doc.append('<h4>Request</h4>')
            doc.extend(self._generate_html_message_docs(input_message, is_request=True))
        
        # Response format
        output_message = self.parser.messages.get(method.output_type)
        if output_message:
            doc.append('<h4>Response</h4>')
            doc.extend(self._generate_html_message_docs(output_message, is_request=False))
        
        # Example
        doc.extend(self._generate_html_example(method))
        
        doc.append('<div class="method-divider"></div>')
        
        return doc
    
    def _generate_html_message_docs(self, message: ProtoMessage, is_request: bool = False) -> List[str]:
        """Generate HTML documentation for a message"""
        doc = []
        
        if not message.fields:
            no_params_text = "No parameters required." if is_request else "Empty response."
            doc.append(f'<p>{no_params_text}</p>')
            return doc
        
        # Parameters table
        doc.append('<table>')
        doc.append('<thead>')
        doc.append('<tr>')
        doc.append('<th>Parameter</th>')
        doc.append('<th>Type</th>')
        doc.append('<th>Required</th>')
        doc.append('<th>Description</th>')
        doc.append('</tr>')
        doc.append('</thead>')
        doc.append('<tbody>')
        
        for field in message.fields:
            if field.is_deprecated:
                continue
                
            required = "Yes" if field.label == "required" else "No"
            if field.label == "repeated":
                formatted_inner_type = self._format_type(field.type, create_links=True)
                field_type = f"Array&lt;{formatted_inner_type}&gt;"
            else:
                field_type = self._format_type(field.type, create_links=True)
            
            description = html.escape(field.comment or "No description available")
            
            doc.append('<tr>')
            doc.append(f'<td><code>{html.escape(field.name)}</code></td>')
            doc.append(f'<td>{field_type}</td>')
            doc.append(f'<td>{required}</td>')
            doc.append(f'<td>{description}</td>')
            doc.append('</tr>')
        
        doc.append('</tbody>')
        doc.append('</table>')
        
        return doc
    

    def _generate_html_example(self, method: ProtoMethod) -> List[str]:
        """Generate HTML example for a method"""
        doc = []
        method_id = method.name.lower()
        
        doc.append('<div class="example-section">')
        doc.append('<h4>Example</h4>')
        
        # Tab navigation
        doc.append('<div class="tab-container">')
        doc.append('<div class="tab-nav">')
        
        # Determine which tabs to show and which should be active first
        has_http = method.http_method and method.http_path
        has_response = method.output_type
        first_tab = True
        
        if has_http:
            active_class = "active" if first_tab else ""
            doc.append(f'<button class="tab-button {active_class}" data-tab="curl-{method_id}">curl</button>')
            doc.append(f'<button class="tab-button" data-tab="http-{method_id}">HTTP</button>')
            first_tab = False
        
        if has_response:
            active_class = "active" if first_tab else ""
            doc.append(f'<button class="tab-button {active_class}" data-tab="response-{method_id}">Response</button>')
        
        doc.append('</div>')  # Close tab-nav
        
        # Tab content
        doc.append('<div class="tab-content">')
        
        # Reset first_tab for content panes
        first_tab = True
        
        # Curl tab
        if has_http:
            active_class = "active" if first_tab else ""
            doc.append(f'<div class="tab-pane {active_class}" id="curl-{method_id}">')
            doc.extend(self._generate_curl_example(method))
            doc.append('</div>')
            first_tab = False
        
        # HTTP request tab
        if has_http:
            doc.append(f'<div class="tab-pane" id="http-{method_id}">')
            doc.append('<pre><code>')
            doc.append(f'{html.escape(method.http_method)} {html.escape(method.http_path)}')
            doc.append('Content-Type: application/json')
            doc.append('Authorization: Bearer YOUR_API_KEY')
            doc.append('')
            
            # Add example request body if applicable
            if method.http_method in ['POST', 'PUT', 'PATCH'] and method.input_type:
                input_message = self.parser.messages.get(method.input_type)
                if input_message and input_message.fields:
                    example_body = self._generate_example_json(input_message)
                    doc.append(html.escape(example_body))
            
            doc.append('</code></pre>')
            doc.append('</div>')
        
        # Response tab
        if has_response:
            output_message = self.parser.messages.get(method.output_type)
            if output_message:
                active_class = "active" if first_tab else ""
                doc.append(f'<div class="tab-pane {active_class}" id="response-{method_id}">')
                doc.append('<pre><code>')
                example_response = self._generate_example_json(output_message)
                doc.append(html.escape(example_response))
                doc.append('</code></pre>')
                doc.append('</div>')
        
        doc.append('</div>')  # Close tab-content
        doc.append('</div>')  # Close tab-container
        doc.append('</div>')  # Close example-section
        
        return doc
    
    def _generate_curl_example(self, method: ProtoMethod) -> List[str]:
        """Generate curl command example for a method"""
        doc = []
        
        # Start building the curl command
        curl_parts = ['curl']
        
        # Add HTTP method if not GET
        if method.http_method and method.http_method.upper() != 'GET':
            curl_parts.append(f'-X {method.http_method.upper()}')
        
        # Add the URL (using placeholder domain)
        url = f'https://saas-api.tmprl.cloud{method.http_path}'
        curl_parts.append(f'"{url}"')
        
        # Add headers
        curl_parts.extend([
            '-H "Content-Type: application/json"',
            '-H "Authorization: Bearer YOUR_API_KEY"'
        ])
        
        # Add request body for POST, PUT, PATCH methods
        if method.http_method in ['POST', 'PUT', 'PATCH'] and method.input_type:
            input_message = self.parser.messages.get(method.input_type)
            if input_message and input_message.fields:
                example_body = self._generate_example_json(input_message)
                # Escape single quotes and wrap in single quotes for shell safety
                escaped_body = example_body.replace("'", "'\"'\"'")
                curl_parts.append(f"-d '{escaped_body}'")
        
        # Generate the curl command string for copying
        if len(curl_parts) <= 3:  # Simple one-liner for GET requests
            curl_command = ' '.join(curl_parts)
        else:  # Multi-line format for complex requests
            curl_lines = [curl_parts[0] + ' \\']
            for part in curl_parts[1:-1]:
                curl_lines.append(f'  {part} \\')
            curl_lines.append(f'  {curl_parts[-1]}')
            curl_command = '\n'.join(curl_lines)
        
        # Create the code block with copy button
        method_id = method.name.lower()
        doc.append('<div class="code-block-container">')
        doc.append(f'<button class="copy-button" data-copy-target="curl-code-{method_id}" title="Copy curl command">Copy</button>')
        doc.append(f'<pre><code id="curl-code-{method_id}" data-curl-command="{html.escape(curl_command)}">')
        
        # Format the display version
        if len(curl_parts) <= 3:  # Simple one-liner for GET requests
            doc.append(html.escape(' '.join(curl_parts)))
        else:  # Multi-line format for complex requests
            doc.append(html.escape(curl_parts[0] + ' \\'))
            for part in curl_parts[1:-1]:
                doc.append(html.escape(f'  {part} \\'))
            doc.append(html.escape(f'  {curl_parts[-1]}'))
        
        doc.append('</code></pre>')
        doc.append('</div>')
        
        return doc
    
    def _collect_referenced_types(self) -> Dict[str, Tuple[Any, str]]:
        """Collect all types (messages and enums) referenced from other packages"""
        if self._referenced_types_cache is not None:
            return self._referenced_types_cache
            
        referenced_types = {}
        
        # Get the main service package (cloudservice)
        main_packages = set()
        for filepath, package in self.parser.packages.items():
            if 'cloudservice' in filepath:
                main_packages.add(package)
        
        def collect_from_message(message: ProtoMessage, visited: set = None, depth: int = 0):
            if visited is None:
                visited = set()
            
            if message.name in visited or depth > 2:  # Limit recursion depth
                return
            visited.add(message.name)
            
            for field in message.fields:
                if field.is_deprecated:
                    continue
                
                base_type = field.type
                if field.label == "repeated":
                    base_type = field.type
                
                if self._should_expand_type(base_type):
                    resolved_message = self._resolve_type_reference(base_type)
                    resolved_enum = self._resolve_enum_reference(base_type)
                    
                    if resolved_message:
                        # Find the package for this type
                        type_package = self._get_type_package(base_type)
                        
                        # Only include types from other packages (not cloudservice)
                        if type_package and type_package not in main_packages and self._is_type_relevant(base_type):
                            referenced_types[base_type] = (resolved_message, type_package)
                            # Recursively collect nested types with increased depth
                            collect_from_message(resolved_message, visited.copy(), depth + 1)
                    elif resolved_enum:
                        # Find the package for this enum type
                        type_package = self._get_type_package(base_type)
                        
                        # Only include enums from other packages (not cloudservice)
                        if type_package and type_package not in main_packages and self._is_type_relevant(base_type):
                            referenced_types[base_type] = (resolved_enum, type_package)
        
        # First collect types directly referenced in method signatures
        direct_types = set()
        
        # Collect referenced types from all service methods
        for service in self.parser.services.values():
            for method in service.methods:
                # Check input type
                if method.input_type:
                    input_message = self.parser.messages.get(method.input_type)
                    if input_message:
                        # Mark direct types from method parameters
                        for field in input_message.fields:
                            if not field.is_deprecated and self._should_expand_type(field.type):
                                base_type = field.type
                                if field.label == "repeated":
                                    base_type = field.type
                                type_package = self._get_type_package(base_type)
                                if type_package and type_package not in main_packages:
                                    direct_types.add(base_type)
                        
                        collect_from_message(input_message)
                
                # Check output type
                if method.output_type:
                    output_message = self.parser.messages.get(method.output_type)
                    if output_message:
                        # Mark direct types from method responses
                        for field in output_message.fields:
                            if not field.is_deprecated and self._should_expand_type(field.type):
                                base_type = field.type
                                if field.label == "repeated":
                                    base_type = field.type
                                type_package = self._get_type_package(base_type)
                                if type_package and type_package not in main_packages:
                                    direct_types.add(base_type)
                        
                        collect_from_message(output_message)
        
        # Include all external types for linking purposes
        # Keep both directly referenced types and their dependencies
        all_external_types = {}
        for type_name, (message, package) in referenced_types.items():
            all_external_types[type_name] = (message, package)
        
        referenced_types = all_external_types
        
        self._referenced_types_cache = referenced_types
        return referenced_types
    
    def _get_type_package(self, type_name: str) -> Optional[str]:
        """Get the package name for a given type"""
        # Handle well-known Google protobuf types
        if type_name.startswith('google.protobuf.'):
            return 'google.protobuf'
        
        # Handle temporal.api.common types
        if type_name.startswith('temporal.api.common.'):
            return 'temporal.api.common.v1'
        
        # If it's a fully qualified name, extract package
        if '.' in type_name:
            parts = type_name.split('.')
            if len(parts) > 1:
                # Remove the last part (type name) to get package
                return '.'.join(parts[:-1])
        
        # Look through all packages to find where this type is defined
        for filepath, package in self.parser.packages.items():
            # Skip mock file paths
            if filepath.startswith('google/protobuf/') or filepath.startswith('temporal/api/common/'):
                continue
                
            # Check if any message in this file matches
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    simple_name = type_name.split('.')[-1]
                    if re.search(rf'message\s+{re.escape(simple_name)}\s*\{{', content):
                        return package
            except FileNotFoundError:
                # Skip files that don't exist (e.g., mock files)
                continue
        
        return None
    
    def _get_service_package(self, service: ProtoService) -> Optional[str]:
        """Get the package name for a given service"""
        if hasattr(service, '_source_file'):
            return self.parser.packages.get(service._source_file)
        return None
    
    def _is_type_relevant(self, type_name: str) -> bool:
        """Determine if a type is relevant enough to include in the types section"""
        
        # Exclude common/generic types that don't add much value
        excluded_types = {
            'google.protobuf.Empty',
            'google.protobuf.StringValue',
            'google.protobuf.Int64Value',
            'google.protobuf.BoolValue',
        }
        
        # Exclude if it's in the excluded list
        if type_name in excluded_types:
            return False
        
        # Exclude types that start with certain prefixes (infrastructure/internal types)
        excluded_prefixes = [
            'temporal.api.enums.',
        ]
        
        for prefix in excluded_prefixes:
            if type_name.startswith(prefix):
                return False
        
        # Allow specific temporal.api.common types but exclude others
        if type_name.startswith('temporal.api.common.'):
            allowed_common_types = {
                'temporal.api.common.v1.Payload'
            }
            return type_name in allowed_common_types
        
        # Allow specific Google protobuf types but exclude others
        if type_name.startswith('google.protobuf.'):
            allowed_google_types = {
                'google.protobuf.Timestamp',
                'google.protobuf.Duration', 
                'google.protobuf.Any'
            }
            return type_name in allowed_google_types
        
        # Exclude very generic or common field names that might not be useful
        simple_name = type_name.split('.')[-1].lower()
        excluded_simple_names = {
            'status',
            'state',
            'error',
            'metadata',
            'config',
            'info',
            'data',
            'result',
        }
        
        if simple_name in excluded_simple_names:
            return False
        
        return True
    
    def _has_direct_dependency(self, type_name: str, direct_types: set) -> bool:
        """Check if a type is referenced by any of the direct types"""
        if type_name in direct_types:
            return True
            
        # Check if this type is used as a field in any direct type
        for direct_type in direct_types:
            direct_message = self._resolve_type_reference(direct_type)
            if direct_message:
                for field in direct_message.fields:
                    if field.is_deprecated:
                        continue
                        
                    base_type = field.type
                    if field.label == "repeated":
                        base_type = field.type
                        
                    if base_type == type_name:
                        return True
                        
                    # Also check for nested dependencies (one level deep)
                    nested_message = self._resolve_type_reference(base_type)
                    if nested_message:
                        for nested_field in nested_message.fields:
                            if nested_field.is_deprecated:
                                continue
                                
                            nested_base_type = nested_field.type
                            if nested_field.label == "repeated":
                                nested_base_type = nested_field.type
                                
                            if nested_base_type == type_name:
                                return True
        
        return False
    
    def _generate_types_section(self) -> List[str]:
        """Generate the types section"""
        referenced_types = self._collect_referenced_types()
        
        if not referenced_types:
            return []
        
        doc = []
        doc.append('<div class="content-section">')
        doc.append('<h2 id="types">Types</h2>')
        doc.append('<p>This section documents all types from external packages used in the CloudService API.</p>')
        
        # Group by package
        packages = {}
        for type_name, (type_obj, package) in referenced_types.items():
            if package not in packages:
                packages[package] = []
            packages[package].append((type_name, type_obj))
        
        # Generate documentation for all types in a flat list
        self._generate_flat_types_list(doc, packages)
        
        doc.append('</div>')
        return doc
    
    def _generate_flat_types_list(self, doc: List[str], packages: Dict[str, List[Tuple[str, Any]]]) -> None:
        """Generate documentation for types (messages and enums) in a flat list"""
        # Collect all types from all packages into a single flat list with deduplication
        all_types = []
        seen_simple_names = set()
        
        for package, types in packages.items():
            for type_name, type_obj in types:
                simple_name = type_name.split('.')[-1]
                # Only add if we haven't seen this simple name before
                if simple_name not in seen_simple_names:
                    all_types.append((type_name, type_obj, package))
                    seen_simple_names.add(simple_name)
        
        # Sort all types alphabetically by simple name
        all_types.sort(key=lambda x: x[0].split('.')[-1])
        
        # Generate documentation for each type
        for type_name, type_obj, package in all_types:
            simple_name = type_name.split('.')[-1]
            type_anchor = f"ref-{simple_name.lower()}"
            
            doc.append('<div class="type-header">')
            doc.append(f'<h4 id="{type_anchor}">{html.escape(simple_name)}</h4>')
            doc.append(f'<button class="link-button" data-anchor="{type_anchor}" title="Copy link to this type">#</button>')
            doc.append('</div>')
            doc.append(f'<p><em>From package:</em> <code>{package}</code></p>')
            
            if hasattr(type_obj, 'comment') and type_obj.comment:
                doc.append(f'<p>{html.escape(type_obj.comment)}</p>')
            
            # Handle message types
            if isinstance(type_obj, ProtoMessage):
                if type_obj.fields:
                    doc.append('<table>')
                    doc.append('<thead>')
                    doc.append('<tr>')
                    doc.append('<th>Field</th>')
                    doc.append('<th>Type</th>')
                    doc.append('<th>Description</th>')
                    doc.append('</tr>')
                    doc.append('</thead>')
                    doc.append('<tbody>')
                    
                    for field in type_obj.fields:
                        if field.is_deprecated:
                            continue
                        
                        field_type = self._format_type(field.type, create_links=True)
                        if field.label == "repeated":
                            field_type = f"Array&lt;{field_type}&gt;"
                        
                        description = html.escape(field.comment or "No description available")
                        
                        doc.append('<tr>')
                        doc.append(f'<td><code>{html.escape(field.name)}</code></td>')
                        doc.append(f'<td>{field_type}</td>')
                        doc.append(f'<td>{description}</td>')
                        doc.append('</tr>')
                    
                    doc.append('</tbody>')
                    doc.append('</table>')
                else:
                    doc.append('<p>No fields defined.</p>')
            
            # Handle enum types
            elif isinstance(type_obj, ProtoEnum):
                if type_obj.values:
                    doc.append('<p><strong>Enum Values:</strong></p>')
                    doc.append('<table>')
                    doc.append('<thead>')
                    doc.append('<tr>')
                    doc.append('<th>Name</th>')
                    doc.append('<th>Value</th>')
                    doc.append('</tr>')
                    doc.append('</thead>')
                    doc.append('<tbody>')
                    
                    for value_name, value_number in sorted(type_obj.values.items(), key=lambda x: x[1]):
                        doc.append('<tr>')
                        doc.append(f'<td><code>{html.escape(value_name)}</code></td>')
                        doc.append(f'<td>{value_number}</td>')
                        doc.append('</tr>')
                    
                    doc.append('</tbody>')
                    doc.append('</table>')
                else:
                    doc.append('<p>No enum values defined.</p>')
            
            # Add some spacing between types
            doc.append('<div style="margin-bottom: 2rem;"></div>')
    
    def _format_type(self, proto_type: str, create_links: bool = False) -> str:
        """Format protobuf type for documentation"""
        type_mapping = {
            'string': 'string',
            'int32': 'integer',
            'int64': 'integer',
            'bool': 'boolean',
            'double': 'number',
            'float': 'number',
            'bytes': 'string (base64)',
        }
        
        base_type = proto_type.split('.')[-1].lower()
        formatted_type = type_mapping.get(base_type, proto_type)
        
        # Create links to external types if requested
        if create_links and self._is_external_type(proto_type):
            simple_name = proto_type.split('.')[-1]
            # Check if it exists in types section, if so link to it
            if self._is_referenced_type(proto_type):
                return f'<a href="#ref-{simple_name.lower()}">{formatted_type}</a>'
            else:
                # For external types not in referenced section, show as plain formatted type
                return formatted_type
        
        return formatted_type
    
    def _is_referenced_type(self, proto_type: str) -> bool:
        """Check if a type is in the types section"""
        referenced_types = self._collect_referenced_types()
        return proto_type in referenced_types
    
    def _is_external_type(self, proto_type: str) -> bool:
        """Check if a type is from an external package (not cloudservice)"""
        # Get the main service package (cloudservice)
        main_packages = set()
        for filepath, package in self.parser.packages.items():
            if 'cloudservice' in filepath:
                main_packages.add(package)
        
        type_package = self._get_type_package(proto_type)
        return type_package and type_package not in main_packages
    
    def _resolve_type_reference(self, proto_type: str) -> Optional[ProtoMessage]:
        """Resolve a type reference to its message definition"""
        # Try exact match first
        if proto_type in self.parser.messages:
            return self.parser.messages[proto_type]
        
        # Try without package prefix
        simple_name = proto_type.split('.')[-1]
        if simple_name in self.parser.messages:
            return self.parser.messages[simple_name]
        
        return None
    
    def _resolve_enum_reference(self, proto_type: str) -> Optional[ProtoEnum]:
        """Resolve a type reference to its enum definition"""
        # Try exact match first
        if proto_type in self.parser.enums:
            return self.parser.enums[proto_type]
        
        # Try without package prefix
        simple_name = proto_type.split('.')[-1]
        if simple_name in self.parser.enums:
            return self.parser.enums[simple_name]
        
        return None
    
    def _should_expand_type(self, proto_type: str) -> bool:
        """Determine if a type should be expanded inline"""
        # Don't expand basic types
        if proto_type in ['string', 'int32', 'int64', 'bool', 'double', 'float', 'bytes']:
            return False
        
        # Allow specific Google protobuf types that we want to document
        if proto_type.startswith('google.protobuf.'):
            allowed_google_types = {
                'google.protobuf.Timestamp',
                'google.protobuf.Duration', 
                'google.protobuf.Any'
            }
            return proto_type in allowed_google_types
        
        # Allow specific temporal.api.common types that we want to document
        if proto_type.startswith('temporal.api.common.'):
            allowed_common_types = {
                'temporal.api.common.v1.Payload'
            }
            return proto_type in allowed_common_types
        
        # Expand our custom types (messages or enums)
        return self._resolve_type_reference(proto_type) is not None or self._resolve_enum_reference(proto_type) is not None
    
    def _generate_example_json(self, message: ProtoMessage) -> str:
        """Generate example JSON for a message"""
        example = {}
        
        for field in message.fields:
            if field.is_deprecated:
                continue
                
            example_value = self._get_example_value(field)
            
            if field.label == "repeated":
                example[field.name] = [example_value]
            else:
                example[field.name] = example_value
        
        return json.dumps(example, indent=2)
    
    def _get_nested_example_value(self, field_type: str) -> Any:
        """Generate example value for nested types"""
        resolved_message = self._resolve_type_reference(field_type)
        if resolved_message:
            nested_example = {}
            for nested_field in resolved_message.fields[:3]:  # Limit to first 3 fields to avoid bloat
                if not nested_field.is_deprecated:
                    nested_example[nested_field.name] = self._get_example_value(nested_field)
            return nested_example
        return f"example_{field_type.split('.')[-1].lower()}"
    
    def _get_example_value(self, field: ProtoField) -> Any:
        """Get example value for a field based on its type"""
        type_examples = {
            'string': 'example_string',
            'int32': 123,
            'int64': 123456789,
            'bool': True,
            'double': 123.45,
            'float': 123.45,
            'bytes': 'base64_encoded_data',
        }
        
        base_type = field.type.split('.')[-1].lower()
        
        if base_type in type_examples:
            return type_examples[base_type]
        elif 'timestamp' in base_type:
            return "2023-12-01T12:00:00Z"
        elif field.name.endswith('_id'):
            return "unique_identifier_123"
        elif 'email' in field.name.lower():
            return "user@example.com"
        elif 'name' in field.name.lower():
            return "example_name"
        elif self._should_expand_type(field.type):
            # Generate nested example for complex types
            return self._get_nested_example_value(field.type)
        else:
            return f"example_{field.name}"

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate HTML API documentation from protobuf files')
    parser.add_argument('proto_dir', help='Directory containing protobuf files')
    parser.add_argument('-o', '--output', default='api_reference.html', help='Output HTML file name')
    parser.add_argument('--service', help='Specific service to document (default: all services)')

    
    args = parser.parse_args()
    
    if not os.path.exists(args.proto_dir):
        print(f"Error: Directory {args.proto_dir} does not exist")
        sys.exit(1)
    
    # Parse the entire repository to build comprehensive type registry
    proto_parser = ProtoParser()
    
    # Find the repository root (look for the temporal/api/cloud structure)
    repo_root = args.proto_dir
    if 'temporal/api/cloud' in args.proto_dir:
        # Navigate up to find the repo root
        repo_root = args.proto_dir.split('temporal/api/cloud')[0]
        if repo_root.endswith('/'):
            repo_root = repo_root[:-1]
        if repo_root == '':
            repo_root = '.'
        repo_root = os.path.join(repo_root, 'temporal/api/cloud')
    
    print(f"Parsing repository: {repo_root}")
    proto_parser.parse_repository(repo_root)
    
    # Summary output
    print(f"Parsed {len(proto_parser.services)} services with {sum(len(s.methods) for s in proto_parser.services.values())} total methods")
    print(f"Found {len(proto_parser.messages)} message types across all packages")
    print(f"Found {len(proto_parser.enums)} enum types")
    print(f"Packages: {len(proto_parser.packages)}")
    
    # Generate documentation
    doc_generator = HTMLDocumentationGenerator(proto_parser)
    
    # Filter by service if specified
    if args.service:
        if args.service not in proto_parser.services:
            print(f"Error: Service {args.service} not found")
            print(f"Available services: {list(proto_parser.services.keys())}")
            sys.exit(1)
        
        # Keep only the specified service
        filtered_services = {args.service: proto_parser.services[args.service]}
        proto_parser.services = filtered_services
    
    # Generate HTML content
    content = doc_generator.generate_html()
    
    # Ensure correct file extension
    if not args.output.endswith('.html'):
        args.output += '.html'
    
    # Write to output file
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Documentation generated successfully: {args.output}")
    print(f"Services documented: {list(proto_parser.services.keys())}")
    print(f"Output format: HTML")

if __name__ == '__main__':
    main() 
