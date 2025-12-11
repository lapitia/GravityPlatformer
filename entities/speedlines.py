import pygame
import random
from pygame.math import Vector2
from constants import COLORS

class Speedline(pygame.sprite.Sprite):
    def __init__(self, position, direction):
        super().__init__()
        self.lifetime = 30 #frames
        self.age = 0
        
        #random properties
        length = random.randint(100,200) #from 100 to 200, vertical length
        thickness = random.randint(1, 3) #1,2,3
        self.image = pygame.Surface((thickness,length), pygame.SRCALPHA)
        self.image.fill(COLORS["WHITE"] + (random.randint(150, 255),)) #a little transparent
        
        #set position and velocity
        self.rect = self.image.get_rect(center=position)
        self.velocity = direction * random.uniform(8, 12) #random.uniform - random floating number between (two included)
        self.offset = Vector2(0, 0) #camera offset

    def update(self):
        self.age += 1
        center = Vector2(self.rect.center)
        center += self.velocity
        self.rect.center = (int(center.x), int(center.y))
        self.image.set_alpha(255 - int(255 * (self.age / self.lifetime)))
        
        #remove when expired
        if self.age >= self.lifetime:
            self.kill()