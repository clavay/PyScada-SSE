"""
        # Add current sessions : updated during the last 24h.
        self.sessions = []
        if apps.is_installed("pyscada.sse"):
            from pyscada.sse.models import Historic
            for hst in Historic.objects.all():
                if hst.is_expired():
                    for var in hst.variables.all():
                        if var_id in self.device.variable_set.all():
                            self.sessions.append(hst)
"""
