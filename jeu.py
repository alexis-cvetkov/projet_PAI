# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""



# =============================================================================
#                       Importation de modules
# =============================================================================

import numpy as np
import sys
from random import choice

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from IPython.display import clear_output
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

#import timeit

# =============================================================================
#                               Classe Jeu
# =============================================================================

class Jeu(QMainWindow):
    
    def __init__(self,nl,nc,marge,px):
        
        """
        Crée un objet de la classe Jeu.
        
        Attributs
        ---------
        
        map_zones : cf init_map
        map_joueurs : cf init_map
        serpent : cf class Serpent
        px : taille d'une case du jeu en pixels.
        
        """
        
        pos_serpent,pos_monstre = (0,0),(nl//2,nc//2)
        self.serpent = Personnage(pos_serpent,direction_initiale=(0,1),type_personnage='Serpent')
        self.monstre = Personnage(pos_monstre,direction_initiale=(0,-1),type_personnage='Monstre') # On place le monstre au centre de la carte.
        self.map_zones = init_map(nl,nc,marge,pos_serpent,pos_monstre,type = 'zones')
        self.map_joueurs = init_map(nl,nc,marge,pos_serpent,pos_monstre,type = 'joueurs')
        
        self.px = px
        self.pause = False
        super().__init__()
        self.setWindowTitle("Mamba")
        self.environnement = Environnement(self,self.map_zones,self.map_joueurs,self.px)
        self.setCentralWidget(self.environnement)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(5000//nc)
        
    def keyPressEvent(self, event):
        
        """ Déplace le serpent lorsqu'on appuie sur une flèche directionnelle. """
        
        if event.isAutoRepeat():
            event.ignore()
           
        key = event.key()
        dl,dc = self.serpent.old_direction # Old direction
        
        if key == Qt.Key_Escape:
            self.close()
        
        elif key == Qt.Key_P: # On passe le jeu en pause / continue
            if self.pause:
                self.timer.start()
            else:
                self.timer.stop()
            self.pause = 1 - self.pause
        
        else:            
            
            if key == Qt.Key_Z:
                dl2,dc2 = (-1,0) # Variable contenant la nouvelle direction 
            elif key == Qt.Key_D:
                dl2,dc2 = (0,1)
            elif key == Qt.Key_S:
                dl2,dc2 = (1,0)
            elif key == Qt.Key_Q:
                dl2,dc2 = (0,-1)
            
            if not (self.pause or dl+dl2 == 0 or dc+dc2 == 0):
                self.serpent.change_direction((dl2,dc2))
            
            else:
                event.ignore()
                
        
    def update(self):
        
        mapZ,mapJ = self.map_zones,self.map_joueurs
        self.serpent.deplace(mapZ,mapJ,self.environnement)
        
        if self.serpent.etat == 2: # On rentre à nouveau dans la zone safe donc on grise la zone dessinée.
            self.grise_zone()
            self.serpent.etat = 0
            
        self.monstre.genere_direction(mapZ,mapJ)
        self.monstre.deplace(mapZ,mapJ,self.environnement)
        
        qApp.processEvents() # Nécéssaire pour éviter le clignotement entre deux frames.
        self.setCentralWidget(self.environnement)
        
        
        
    def grise_zone(self):
        
        path = path_finding(self.map_zones,self.serpent.depart,self.serpent.arrivee)
        path.reverse()
        
        for case in self.serpent.corps:
            self.map_zones[case] = 0
        
        contour = self.serpent.corps + path # L'ordre des points est important pour delimiter le polygone correctement.
        polygon = Polygon(contour)
        
        L,C = zone_a_tester(contour)
        nl,nc = L.shape 
        points_a_griser = self.serpent.corps
        for i in range(nl):
            for k in range(nc):
                coordonnees = L[i,k],C[i,k]
                point = Point(coordonnees)
                if polygon.contains(point):
                    points_a_griser.append(coordonnees)
                    self.map_zones[coordonnees] = 0
                    pass
        
        self.environnement.carte.grise_dessin(points_a_griser,self.environnement)
        qApp.processEvents() # Nécéssaire pour éviter le clignotement entre deux frames.
        self.setCentralWidget(self.environnement)
        
        self.serpent.corps = []
        


# =============================================================================
#                            Classe Personnage
# =============================================================================



class Personnage():
    
    def __init__(self,position_initiale,direction_initiale,type_personnage):
            
        """
        Crée le personnage.
        
        Attributs
        ---------
        
        position : tuple donnant la position du personnage dans la matrice.
        direction : string donnant la direction.
        corps : liste des positions des cases mangées dans le cas du serpent.
        type : le type de personnage ('Monstre' ou 'Serpent').
        old_direction : la direction lors du dernier déplacement du personnage.
        depart : la dernière case safe ou est passé le serpent avant d'entrer en zone pas safe.
        arrivee : la première case safe ou rentre le serpent avant de quitter la zone pas safe.
        
        """
        
        self.position = position_initiale
        self.direction_instant = direction_initiale # la direction à un instant t
        self.corps = []
        self.type = type_personnage
        self.old_direction = '' # direction lors de la dernière update de la map 
        self.etat = 0
        self.depart = (0,0)
        self.arrivee = (0,0)
        
    def change_direction(self,direction):
        
        self.direction_instant = direction
    
    def deplace(self,map_zones,map_joueurs,environnement):
        
        """ Modifie les matrices map_zones et map_joueurs lors du déplacement du personnage. """
        
        if self.direction_instant == (0,0):
            return
        
        l,c = self.position
        dl,dc = self.direction_instant
        nl,nc = map_joueurs.shape
    
        # Calcul les nouvelles positions.
        
        old_position = l,c
        new_position = (l+dl)%nl,(c+dc)%nc
        self.test_collisions(new_position) # Verifie que le serpent ne meurt pas pendant son déplacement.
        
        self.position = new_position
        old_zone,new_zone = map_zones[old_position],map_zones[new_position]
        
        if  old_zone != new_zone : # Changement de zone.            
            self.etat += 1
            if self.etat == 1:
                self.depart = l,c
            else:
                self.arrivee = new_position
        
        if self.type == 'Serpent':
            
            if old_zone:
                map_joueurs[old_position] = -1            
            else:
                map_joueurs[old_position] = 0
            
            map_joueurs[new_position] = 1
            
            if new_zone:
                self.corps.append(new_position)
        
        elif self.type == 'Monstre':
            
            map_joueurs[old_position] = 0
            map_joueurs[new_position] = 2
        
        environnement.carte.redessine(old_position,new_position,old_zone,new_zone,
                                      environnement,self.type)
        
        self.old_direction = self.direction_instant
        
    
    def genere_direction(self,map_zones,map_joueurs,IA='aleatoire'):
        
        if IA == 'aleatoire':
            
            l,c = self.position
            nl,nc = map_zones.shape
            D = [(1,0),(-1,0),(0,1),(0,-1)] # Bas, Haut, Droite, Gauche.
            directions_possibles = D.copy()
            for d in D:
                dl,dc = d
                p = (l+dl)%nl,(c+dc)%nc
                if not map_zones[p]:
                    directions_possibles.remove(d)
            if directions_possibles == []: # Toutes les cases autour sont grises.
                self.change_direction((0,0)) # Le monstre est immobile.
            else:
                 self.change_direction(choice(directions_possibles))
            return           
    
    def test_collisions(self,new_position):
        pass
    
    
    
# =============================================================================
#                            Classe Environnement
# =============================================================================
        
    
    
class Environnement(QGraphicsView):
    
    """ Classe qui dessine la carte à partir de map_zones et map_joueurs. """
    
    def __init__(self,parent,map_zones,map_joueurs,px):
        
        super().__init__(parent)
        self.carte = Carte(self,map_zones,map_joueurs,px)
        self.setScene(self.carte)
        

class Carte(QGraphicsScene):
    
    def __init__(self,parent,map_zones,map_joueurs,px):
        
        super().__init__(parent)
        nl,nc = map_zones.shape
        self.setSceneRect(0,0,nc*px,nl*px)
        
        self.brosse_grise = QBrush(QColor(128,128,128),Qt.SolidPattern)
        self.brosse_blanche = QBrush(QColor(255,255,255),Qt.SolidPattern)
        self.brosse_marron = QBrush(QColor(88,41,0),Qt.SolidPattern)
        self.brosse_rouge = QBrush(QColor(255,0,0),Qt.SolidPattern)
        self.brosse_bleue = QBrush(QColor(0,0,255),Qt.SolidPattern)
        self.stylo = QPen(Qt.black,1,Qt.SolidLine)
        self.px = px
        
        for i in range(nl):
            for k in range(nc):
                
                zone_danger,type_joueur = map_zones[i,k],map_joueurs[i,k]
                
                if zone_danger: # Zone non-safe
                    self.addRect(k*px,i*px,px,px,self.stylo,self.brosse_blanche)
                else: # Zone safe
                    self.addRect(k*px,i*px,px,px,self.stylo,self.brosse_grise)
                
                if type_joueur == 1: # Tete du serpent
                    self.addRect(k*px,i*px,px,px,self.stylo,self.brosse_rouge)
                elif type_joueur == -1: # Corps du serpent
                    self.addRect(k*px,i*px,px,px,self.stylo,self.brosse_marron)
                elif type_joueur == 2: # Monstre
                    self.addRect(k*px,i*px,px,px,self.stylo,self.brosse_bleue)    
        return
    
    def redessine(self,old_position,new_position,old_zone,new_zone,environnement,
                  type_personnage):
        
        i,k = old_position
        px = self.px
        
        if type_personnage == 'Serpent':
            
            if old_zone:
                self.addRect(k*px,i*px,px,px,self.stylo,self.brosse_marron)
                
            else:
                self.addRect(k*px,i*px,px,px,self.stylo,self.brosse_grise)
            
            i,k = new_position
            self.addRect(k*px,i*px,px,px,self.stylo,self.brosse_rouge)    
            
        else:
            self.addRect(k*px,i*px,px,px,self.stylo,self.brosse_blanche)
            i,k = new_position
            self.addRect(k*px,i*px,px,px,self.stylo,self.brosse_bleue)            
        
        environnement.setScene(self)
        
    def grise_dessin(self,zone_a_griser,environnement):
        
        px = self.px
        
        for case in zone_a_griser:
            i,k = case
            self.addRect(k*px,i*px,px,px,self.stylo,self.brosse_grise)
        
        environnement.setScene(self)    
            


# =============================================================================
#                           Fonctions secondaires
# =============================================================================


def init_map(nl,nc,marge,pos_serpent,pos_monstre,type):
    
    """
    Fonction qui initialise les matrices correspondant au plateau de jeu.
    
    Paramètres
    ----------
    
    nl : int
        Nombre le lignes du plateau de jeu.
    nc : int
        Nombre de colonnes du plateau de jeu.
    marge : int
        La marge définissant la zone safe.
    type : str
        Le type de matrice a créer. type = 'zones' (resp. 'joueurs') pour initialiser la matrice des zones
        (resp. des joueurs).
    
    Renvoie
    -------
    
    M : int array
        Si type = 'zones', M[i,k] = 0 si la case (i,k) est dans la zone safe et M[i,k] = 1 si elle est dans la zone
        de danger. Initiallement, une bordure de taille "marge" est créee pour la zone safe. Le reste de la carte
        correspond à la zone de danger.
        Si type = 'joueurs', M[i,k] = 1 la où le joueur se situe, -1 sur les cases non-safe mangées par le joueurs et
        0 pour le reste des cases.
        
    """
    
    if type == 'zones':
        
        M = np.zeros((nl,nc),dtype=int)
        M[marge:nl-marge,marge:nc-marge] = 1    
        
    elif type == 'joueurs':
        M = np.zeros((nl,nc),dtype=int)
        M[pos_serpent] = 1
        M[pos_monstre] = 2
        
    return M


def path_finding(grid,depart,arrivee):
    
    queue = [[depart]]
    seen = set([depart])
    nl,nc = grid.shape
    
    while queue:       
        
        path = queue.pop(0)
        x, y = path[-1]
        
        if (x,y) == arrivee:
            return path
        
        for x2, y2 in ((x+1,y), (x-1,y), (x,y+1), (x,y-1)):            
            if 0 <= x2 < nl and 0 <= y2 < nc and grid[x2][y2] != 1 and (x2, y2) not in seen:
                queue.append(path + [(x2, y2)])
                seen.add((x2, y2))

def zone_a_tester(contour):
    
    lignes = [position[0] for position in contour]
    colonnes = [position[1] for position in contour]
    
    l_min,l_max = min(lignes),max(lignes)
    c_min,c_max = min(colonnes),max(colonnes)
    
    l = np.arange(l_min,l_max+1)
    c = np.arange(c_min,c_max+1)    
    L,C = np.meshgrid(l,c)
    
    return L,C
    
# =============================================================================
#                               Fonction Main
# =============================================================================



def main(nl,nc,marge,px):
    
    """ Lance le jeu et affiche l'interface graphique."""
    
    app = QApplication(sys.argv)
    jeu = Jeu(nl,nc,marge,px)
    M = jeu.map_zones
    jeu.show()
    #jeu.resize(1600,900)
    app.exec_()
    #sys.exit(app.exec_())
    return M

    
M = main(100,200,10,5)
#print(M)