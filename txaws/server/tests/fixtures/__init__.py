try:
    import venusian
except ImportError:
    method = lambda function: function
    has_venusian = False
else:
    from txaws.server.method import method
    has_venusian = True
