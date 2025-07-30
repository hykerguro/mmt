_all = all
_any = any


def from_private_user(user_id):
    return lambda message: (message["peer_id"]["_"] == "PeerUser"
                            and str(message["peer_id"]["user_id"]) == str(user_id))


def from_channel(channel_id):
    return lambda message: (message["peer_id"]["_"] == "PeerChannel"
                            and str(message["peer_id"]["channel_id"]) == str(channel_id))


def has_keyword(keyword):
    return lambda message: keyword in message["message"]


def has_media():
    return lambda message: message["media"] is not None


def has_photo():
    return all(has_media(), lambda message: message["media"]["_"] == "MessageMediaPhoto")


def has_document():
    def _cond(message):
        media = message["media"]
        if media is None or media["_"] != "MessageMediaDocument":
            return False
        document = media["document"]
        if document is None or document["_"] != "Document":
            return False
        return True

    return _cond


def has_file():
    def _cond(message):
        attributes = message["media"]["document"]["attributes"]
        return len(attributes) == 1 and attributes[0]["_"] == "DocumentAttributeFilename"

    return all(has_document(), _cond)


def has_video():
    def _cond(message):
        attributes = message["media"]["document"]["attributes"]
        for attribute in attributes:
            if attribute["_"] == "DocumentAttributeVideo":
                return True
        return False

    return all(has_document(), _cond)


def has_stcker():
    def _cond(message):
        attributes = message["media"]["document"]["attributes"]
        for attribute in attributes:
            if attribute["_"] == "DocumentAttributeSticker":
                return True
        return False

    return _cond


def all(*predicates):
    def _and(message):
        for predicate in predicates:
            if not predicate(message):
                return False
        return True

    return _and


def any(*predicates):
    def _or(message):
        for predicate in predicates:
            if predicate(message):
                return True
        return False

    return _or


def true():
    return lambda message: True


def false():
    return lambda message: False
