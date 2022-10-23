class ITUMobilUtils:
    def get_timestamp_between_brackets(self, tarih="()"):
        return tarih[tarih.find("(") + 1 : tarih.find(")")]
