import data_handler
import strategy
import ui

def main():
    """
    The main function to run the trading terminal.
    """
    # --- Initialization ---
    print("Initializing terminal...")
    try:
        market_data = data_handler.load_data_from_csv()
        strategy_processor = strategy.StrategyProcessor()
        data_feed = data_handler.replay_data(market_data)

        print("Initialization complete. Starting terminal application...")
        print("Press Ctrl+C to exit.")

        # --- Main Application Loop ---
        for tick in data_feed:
            # 1. Process the current tick to update strategy state
            current_state = strategy_processor.process_tick(tick)

            # 2. Display the updated state in the terminal
            ui.display_terminal(current_state)

    except FileNotFoundError:
        print(f"Error: Data file not found at '{data_handler.config.CSV_FILE_PATH}'. Please ensure the file exists.")
    except KeyboardInterrupt:
        print("\nExiting terminal. Goodbye!")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
