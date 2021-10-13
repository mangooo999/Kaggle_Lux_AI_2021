
# class LazyWrapper(object):
#     def __init__(self, func):
#         self.func = func
#         self.value = None
#     def __call__(self):
#         if self.value is None:
#             self.value = self.func()
#         return self.value

class LazyWrapper(object):
    def __init__(self, func):
        self.func = func
    def __call__(self):
        try:
            return self.value
        except AttributeError:
            self.value = self.func()
            return self.value