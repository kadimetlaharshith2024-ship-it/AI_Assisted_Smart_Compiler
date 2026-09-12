class NodeVisitor:
    def visit(self, node, *args, **kwargs):
        if node is None:
            return None
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node, *args, **kwargs)

    def generic_visit(self, node, *args, **kwargs):
        # Fallback if a specific node visit handler isn't explicitly defined
        if hasattr(node, '__dict__'):
            for _, value in node.__dict__.items():
                if isinstance(value, list):
                    for item in value:
                        if hasattr(item, '__class__') and hasattr(item, 'to_dict') or hasattr(item, '__dict__'):
                            self.visit(item, *args, **kwargs)
                elif hasattr(value, '__class__') and (hasattr(value, 'to_dict') or hasattr(value, '__dict__')):
                    self.visit(value, *args, **kwargs)
        return None