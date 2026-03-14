with open("src/application/di_container.py") as f:
    content = f.read()

# Fix the resolution thread-local initialization
old_resolve = """            if interface in self._singletons:
                if not isinstance(self._singletons[interface], interface):
                    msg = f"Expected {interface}, got {type(self._singletons[interface])}"
                    raise TypeError(msg)
                return cast(T, self._singletons[interface])

            if interface in self._local.resolving:"""

new_resolve = """            if interface in self._singletons:
                if not isinstance(self._singletons[interface], interface):
                    msg = f"Expected {interface}, got {type(self._singletons[interface])}"
                    raise TypeError(msg)
                return cast(T, self._singletons[interface])

            if not hasattr(self._local, "resolving"):
                self._local.resolving = set()

            if interface in self._local.resolving:"""

content = content.replace(old_resolve, new_resolve)

with open("src/application/di_container.py", "w") as f:
    f.write(content)
