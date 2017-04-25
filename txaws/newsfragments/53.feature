txAWS now raises a CredentialsNotFoundError when it cannot locate credentials. Catching the previously-raised ValueError is now deprecated.
