import numpy as np 
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class RealTime3DMap:
    def __init__(self):
        # Initialize empty lists to store x, y, z coordinates
        self.x_data, self.y_data, self.z_data = [], [], []


        # Set up the 3D plot
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        self.ax.set_title('Real-Time 3D Map of XYZ Coordinates')


    def update_plot(self, x, y, z):
        """
        Update the 3D plot with new x, y, z coordinates.
        """
        if x is not None and y is not None and z is not None:
            # Append new coordinates to the lists
            self.x_data.append(x)
            self.y_data.append(y)
            self.z_data.append(z)

            # Clear the previous plot and redraw
            self.ax.clear()
            self.ax.scatter(self.x_data, self.y_data, self.z_data, c='r', marker='o')
            self.ax.set_xlabel('X')
            self.ax.set_ylabel('Y')
            self.ax.set_zlabel('Z')
            self.ax.set_title('Real-Time 3D Map of XYZ Coordinates')
            plt.draw()
            # plt.pause(0.0001)  # Pause to allow the plot to update

    def show(self):
        plt.show()




class RealTime2DGridMap:
    def __init__(self, grid_size=(25, 25), x_max=500, y_max=500):
        self.grid_size = grid_size
        self.x_max = x_max
        self.y_max = y_max
        self.grid = np.zeros(grid_size)
        
        # Set up the plot
        self.fig, self.ax = plt.subplots()
        self.im = self.ax.imshow(self.grid, cmap='viridis', vmin=0, vmax=1,
                                 extent=[0, x_max, 0, y_max], origin='lower')
        self.ax.set_title("Real-Time 2D Grid Map")
        plt.colorbar(self.im, ax=self.ax, label="Value")
        
        # Initialize FuncAnimation to call self.update_plot every ms
        self.ani = FuncAnimation(self.fig, self.update_plot, interval=1)
    
    def update_plot(self, frame):
        """
        Update the grid and the plot.
        This function is automatically called every interval (1 ms in this example).
        """
        # Assume that self.current_x and self.current_y have been updated externally.
        x = self.current_x
        y = self.current_y
        
        # Convert (x, y) to grid indices.
        grid_x = min(int((x / self.x_max) * self.grid_size[1]), self.grid_size[1]-1)
        grid_y = min(int((y / self.y_max) * self.grid_size[0]), self.grid_size[0]-1)
        
        # Update the grid cell to 1
        self.grid[grid_y, grid_x] = 1  
        
        # Update the image data and redraw the figure
        self.im.set_data(self.grid)
        return self.im  # Returning is useful for blitting (optional)
    
    def update_coordinates(self, x, y):
        """
        This method can be called from your data fetching loop to update the coordinates.
        """
        self.current_x = x
        self.current_y = y

    def heat_propagation(self, x, y):
        grid_x = min(int((x / self.x_max) * self.grid_size[1]), self.grid_size[1] - 1)
        grid_y = min(int((y / self.y_max) * self.grid_size[0]), self.grid_size[0] - 1)

        # Constante de diffusion
        alpha = 0.1

        # Nouvelle grille pour stocker les valeurs mises à jour
        new_grid = np.copy(self.grid)

        # Mettre à jour chaque cellule en fonction de ses voisines
        for i in range(1, self.grid_size[0] - 1):
            for j in range(1, self.grid_size[1] - 1):
                new_grid[i, j] = self.grid[i, j] + alpha * (
                    self.grid[i-1, j] + self.grid[i+1, j] + self.grid[i, j-1] + self.grid[i, j+1] - 4 * self.grid[i, j]
                )

        # Appliquer la mise à jour de la chaleur au point spécifique
        new_grid[grid_y, grid_x] = 1  

        # Mettre à jour la grille actuelle
        self.grid = new_grid

        # Rafraîchir l'affichage
        self.im.set_data(self.grid)
        self.fig.canvas.draw_idle()

    
    def show(self):
        plt.show()