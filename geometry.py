import pygame


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Substituto para o MathHelper.Clamp do XNA."""
    return max(min_val, min(value, max_val))


class Circle:
    """Representa um círculo 2D para detecção de colisão."""

    def __init__(self, position: pygame.math.Vector2, radius: float):
        self.center = position
        self.radius = radius

    def intersects(self, rectangle: pygame.Rect) -> bool:
        """
        Determina se o círculo intercepta um retângulo.
        Retorna True se sobrepuserem, False caso contrário.
        """
        # Encontra o ponto mais próximo no retângulo em relação ao centro do círculo
        v_x = clamp(self.center.x, rectangle.left, rectangle.right)
        v_y = clamp(self.center.y, rectangle.top, rectangle.bottom)
        closest_point = pygame.math.Vector2(v_x, v_y)

        direction = self.center - closest_point
        distance_squared = direction.length_squared()

        return (distance_squared > 0) and (distance_squared < (self.radius * self.radius))


def get_intersection_depth(rect_a: pygame.Rect, rect_b: pygame.Rect) -> pygame.math.Vector2:
    """
    Calcula a profundidade assinada de intersecção entre dois retângulos.
    Essencial para a resolução de colisão empurrando os objetos na direção correta.
    """
    # Calcula as meias larguras e alturas
    half_width_a = rect_a.width / 2.0
    half_height_a = rect_a.height / 2.0
    half_width_b = rect_b.width / 2.0
    half_height_b = rect_b.height / 2.0

    # Calcula os centros exatos (usando float para precisão matemática,
    # já que o Pygame Rect armazena apenas inteiros)
    center_a_x = rect_a.left + half_width_a
    center_a_y = rect_a.top + half_height_a
    center_b_x = rect_b.left + half_width_b
    center_b_y = rect_b.top + half_height_b

    distance_x = center_a_x - center_b_x
    distance_y = center_a_y - center_b_y
    min_distance_x = half_width_a + half_width_b
    min_distance_y = half_height_a + half_height_b

    # Se não houver intersecção, retorna vetor zero
    if abs(distance_x) >= min_distance_x or abs(distance_y) >= min_distance_y:
        return pygame.math.Vector2(0, 0)

    # Calcula e retorna a profundidade da intersecção
    depth_x = (min_distance_x - distance_x) if distance_x > 0 else (-min_distance_x - distance_x)
    depth_y = (min_distance_y - distance_y) if distance_y > 0 else (-min_distance_y - distance_y)

    return pygame.math.Vector2(depth_x, depth_y)


def get_bottom_center(rect: pygame.Rect) -> pygame.math.Vector2:
    """
    Obtém a posição do centro da borda inferior do retângulo.
    O Pygame possui o atributo 'midbottom', então apenas o convertemos para Vector2.
    """
    return pygame.math.Vector2(rect.midbottom)