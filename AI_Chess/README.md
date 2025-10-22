# AI Chess Game

This project is a simple implementation of a chess game using Python and Pygame. It includes a graphical user interface (GUI) for playing chess against another player. The game adheres to the standard rules of chess, including special moves such as castling, en passant, and pawn promotion.

## Project Structure

- `ui.py`: Contains the main logic for the chess game, including game state management, user interface, and game rules. This file defines the `GameState` class, which manages the board, move log, current player's turn, castling rights, and en passant status. It will also include methods for saving and loading the game state to and from a file.
  
- `images/`: A directory containing images for the chess pieces used in the game. Ensure that the images are named according to the piece type (e.g., `wp.png` for white pawn, `bk.png` for black king, etc.).

## Features

- Play chess with a friend on the same computer.
- Supports all standard chess rules, including:
  - Castling
  - En passant
  - Pawn promotion
- Visual representation of the chess board and pieces.
- Move history display.
- Ability to reset the game.
- Undo the last move.
- Save and load game state.

## Requirements

- Python 3.x
- Pygame library

## How to Run the Game

1. Ensure you have Python 3.x installed on your computer.
2. Install the Pygame library if you haven't already:
   ```
   pip install pygame
   ```
3. Download or clone the repository to your local machine.
4. Navigate to the project directory in your terminal.
5. Run the game using the following command:
   ```
   python ui.py
   ```

## Saving and Loading Games

The game includes functionality to save the current game state to a file and load it later. This feature allows players to pause their game and resume it at a later time.

## License

This project is open-source and available for anyone to use and modify.