class MicroSignalAgent:
    """
    Kullanıcının mikro geri bildirimlerini (örn. yemek)
    küçük ama anlamlı bir değere çevirir.

    Beklenen input:
        +1  -> olumlu
        -1  -> olumsuz
         0  -> yok / belirtilmedi
    """

    def score(self, meal_feedback: int | None) -> int:
        if meal_feedback == 1:
            return +1
        if meal_feedback == -1:
            return -1
        return 0
