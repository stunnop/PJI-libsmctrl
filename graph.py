import matplotlib.pyplot as plt
import pandas as pd

# Read data from CSV file
data = pd.read_csv('partition_performance.csv')

# Extract the data for each column
labels = data['Exe']
x = data['TPCS']
y = data['Average Completion Time (seconds)']

# Create a 2D scatter plot
plt.figure(figsize=(10, 6))
plt.scatter(x, y, c='b', marker='o')
plt.plot(x, y, linestyle='-', color='b', marker='o')

# Label each point with its corresponding label
for i, label in enumerate(labels):
    plt.text(x[i], y[i], label, fontsize=9, ha='right')

# Label the axes
plt.xlabel('TPCS')
plt.ylabel('Average Completion Time (seconds)')

# Set the title
plt.title("Temps d'exécution par TPCs alloués")

# Show the plot
plt.grid(True)
# Save the plot as an image file
plt.savefig('scatter_plot.png', format='png')
