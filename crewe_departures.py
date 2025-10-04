import tkinter as tk
from tkinter import ttk
from nredarwin.webservice import DarwinLdbSession
from datetime import datetime
from dotenv import load_dotenv
import os

class CreweDeparturesGUI:
    def __init__(self, api_key, time_width, dest_width, plat_width, status_width, stops_width, ticker_start_delay, ticker_speed, services_limit):
        self.api_key = api_key
        self.time_width = time_width
        self.dest_width = dest_width
        self.plat_width = plat_width
        self.status_width = status_width
        self.stops_width = stops_width
        self.ticker_start_delay = ticker_start_delay
        self.ticker_speed = ticker_speed
        self.services_limit = services_limit
        self.ticker_positions = {}  # Track ticker offset per row
        self.top = tk.Tk()
        self.top.title("Crewe Station Departures Board")
        self.top.configure(background=os.getenv('BACKGROUND_COLOR', 'black'))
        self.darwin_session = DarwinLdbSession(
            wsdl='https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx?ver=2010-11-01',
            api_key=api_key
        )
        self.create_widgets()
        self.refresh_departures()  # Initial load
        self.auto_refresh()  # Start auto-refresh loop

    def create_widgets(self):
        # Load configurable font sizes
        title_font_size = int(os.getenv('TITLE_FONT_SIZE', '24'))
        body_font_size = int(os.getenv('BODY_FONT_SIZE', '14'))
        heading_font_size = int(os.getenv('HEADING_FONT_SIZE', '14'))

        # Load configurable colors
        title_color = os.getenv('TITLE_COLOR', 'orange')
        clock_color = os.getenv('CLOCK_COLOR', 'orange')
        text_color = os.getenv('TEXT_COLOR', 'orange')
        background_color = os.getenv('BACKGROUND_COLOR', 'black')
        selection_color = os.getenv('SELECTION_COLOR', 'orange')

        # Custom font setup
        try:
            board_font = (os.getenv('Dot Matrix', 'Dot Matrix'), body_font_size)
            heading_font = (os.getenv('Dot Matrix', 'Dot Matrix'), heading_font_size, "bold")
            title_font = (os.getenv('Dot Matrix', 'Dot Matrix'), title_font_size, "bold")
        except tk.TclError:
            board_font = ("Courier New", body_font_size)
            heading_font = ("Courier New", heading_font_size, "bold")
            title_font = ("Courier New", title_font_size, "bold")

        # Use grid for layout
        self.top.grid_rowconfigure(1, weight=1)  # Allow Treeview row to expand
        self.top.grid_columnconfigure(0, weight=1)  # Expand main column

        # Title and Clock in header
        tk.Label(self.top, text="Crewe Station Departures", font=title_font, fg=title_color, bg=background_color).grid(row=0, column=0, sticky="ew", pady=5)
        self.clock_text = tk.Label(self.top, font=board_font, fg=clock_color, bg=background_color)
        self.clock_text.grid(row=1, column=0, sticky="ew", pady=2)

        # Refresh button
        btn_font = ("Arial", 10)
        refresh_btn = tk.Button(self.top, text="Manual Refresh", font=btn_font, bg=background_color, fg=clock_color, 
                                command=self.refresh_departures, highlightthickness=0)
        refresh_btn.grid(row=2, column=0, sticky="ew", pady=5)

        # Treeview for tabular display (no scrollbars)
        columns = ('Time', 'Destination', 'Platform', 'Status', 'Stops')
        self.tree = ttk.Treeview(self.top, columns=columns, show='headings', height=20)
        
        # Configure column headings and widths (in pixels, ~8 pixels/char for monospaced)
        self.tree.heading('Time', text='Time')
        self.tree.heading('Destination', text='Destination')
        self.tree.heading('Platform', text='Platform')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Stops', text='Stops')
        
        self.tree.column('Time', width=self.time_width * 8, minwidth=self.time_width * 8, anchor='w', stretch=False)
        self.tree.column('Destination', width=self.dest_width * 8, minwidth=self.dest_width * 8, anchor='w', stretch=False)
        self.tree.column('Platform', width=self.plat_width * 8, minwidth=self.plat_width * 8, anchor='w', stretch=False)
        self.tree.column('Status', width=self.status_width * 8, minwidth=self.status_width * 8, anchor='w', stretch=False)
        self.tree.column('Stops', width=self.stops_width * 8, minwidth=self.stops_width * 8, anchor='w', stretch=True)
        
        # Style for configurable text and background, no borders
        style = ttk.Style()
        style.theme_use('alt')  # Try 'alt' theme for better border control
        style.configure('Treeview', background=background_color, foreground=text_color, fieldbackground=background_color, font=board_font, 
                        highlightthickness=0, borderwidth=0, padding=0)
        style.configure('Treeview.Heading', background=background_color, foreground=text_color, font=heading_font, 
                        highlightthickness=0, borderwidth=0)
        style.map('Treeview', background=[('selected', selection_color)], foreground=[('selected', background_color)])
        style.map('Treeview.Heading', background=[('active', background_color)])
        
        # Grid placement (no scrollbars)
        self.tree.grid(row=3, column=0, sticky="nsew")

        # Configure grid weights
        self.top.grid_rowconfigure(3, weight=1)  # Treeview row expands
        self.top.grid_columnconfigure(0, weight=1)  # Main column expands

        # Footer label (for errors only)
        self.footer_text = tk.Label(self.top, font=board_font, fg=text_color, bg=background_color)
        self.footer_text.grid(row=4, column=0, sticky="ew", pady=5)

        self.update_clock()

    def fetch_crewe_departures(self):
        try:
            board = self.darwin_session.get_station_board('CRE', self.services_limit)  # Positional argument
            if not board or not board.train_services:
                self.footer_text.config(text="No departures found or API error. Check your key!")
                return
            
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            now = datetime.now().strftime('%H:%M:%S')
            self.tree.heading('Time', text=f'Time (as of {now})')
            
            service_count = 0
            self.ticker_positions.clear()  # Reset ticker positions
            for service in board.train_services:
                std = (service.std or "N/A")[:self.time_width] + ("..." if len(service.std or "") > self.time_width else "")
                destination = (service.destination_text or "N/A")[:self.dest_width] + ("..." if len(service.destination_text or "") > self.dest_width else "")
                platform = (service.platform or "TBD")[:self.plat_width] + ("..." if len(service.platform or "") > self.plat_width else "")
                etd = service.etd
                
                if hasattr(service, 'is_cancelled') and service.is_cancelled:
                    status = "Cancelled"[:self.status_width] + ("..." if len("Cancelled") > self.status_width else "")
                elif etd and etd != service.std and etd != "On time":
                    status = f"Delayed ({etd})"[:self.status_width] + ("..." if len(f"Delayed ({etd})") > self.status_width else "")
                else:
                    status = "On Time"[:self.status_width] + ("..." if len("On Time") > self.status_width else "")
                
                # Fetch stops
                stops_full = "N/A"
                if hasattr(service, 'service_id') and service.service_id:
                    try:
                        service_details = self.darwin_session.get_service_details(service.service_id)
                        if service_details and hasattr(service_details, 'subsequent_calling_points'):
                            stop_names = [cp.location_name for cp in service_details.subsequent_calling_points]
                            stops_full = ', '.join(stop_names) if stop_names else "Direct"
                        else:
                            print(f"No subsequent_calling_points for service {service.service_id}")  # Debug
                    except Exception as e:
                        print(f"Error fetching service details for {service.service_id}: {e}")
                
                # Insert initial row with truncated or full Stops
                stops_display = stops_full if len(stops_full) <= self.stops_width else stops_full[:self.stops_width] + "..."
                item_id = self.tree.insert('', 'end', values=(std, destination, platform, status, stops_display))
                if len(stops_full) > self.stops_width:
                    self.ticker_positions[item_id] = {'full_text': stops_full, 'position': 0}
                    self.top.after(self.ticker_start_delay, lambda id=item_id: self.start_ticker(id))
                service_count += 1
        
        except Exception as e:
            self.footer_text.config(text=f"API call failed: {e}. Ensure your API key is valid and the WSDL URL is current.")

    def start_ticker(self, item_id):
        if item_id in self.ticker_positions:
            pos_data = self.ticker_positions[item_id]
            full_text = pos_data['full_text']
            current_pos = pos_data['position']
            display_width = self.stops_width
            
            # Calculate the substring to show
            if current_pos >= len(full_text):
                pos_data['position'] = 0  # Loop back
                current_pos = 0
            end_pos = current_pos + display_width
            ticker_text = full_text[current_pos:end_pos]
            if end_pos < len(full_text):
                ticker_text += " " * (display_width - len(ticker_text))  # Pad with spaces
            
            # Update the Treeview item
            for item in self.tree.get_children():
                if item == item_id:
                    values = self.tree.item(item, 'values')
                    values = list(values)
                    values[4] = ticker_text
                    self.tree.item(item, values=values)
                    break
            
            # Increment position for next step
            pos_data['position'] = current_pos + 1
            self.top.after(self.ticker_speed, lambda: self.start_ticker(item_id))

    def refresh_departures(self):
        self.fetch_crewe_departures()

    def update_clock(self):
        now = datetime.now()
        self.clock_text.config(text=now.strftime("%H:%M:%S"))  # Simplified to just time
        self.clock_text.after(1000, self.update_clock)

    def auto_refresh(self):
        self.refresh_departures()
        self.top.after(30000, self.auto_refresh)

    def start(self):
        self.top.mainloop()

if __name__ == "__main__":
    load_dotenv()
    API_KEY = os.getenv('API_KEY')
    
    # Load column widths, ticker settings, and services limit with defaults (in characters)
    time_width = int(os.getenv('COLUMN_TIME_WIDTH', '8'))
    dest_width = int(os.getenv('COLUMN_DEST_WIDTH', '30'))
    plat_width = int(os.getenv('COLUMN_PLATFORM_WIDTH', '8'))
    status_width = int(os.getenv('COLUMN_STATUS_WIDTH', '25'))
    stops_width = int(os.getenv('COLUMN_STOPS_WIDTH', '40'))
    ticker_start_delay = int(os.getenv('TICKER_START_DELAY', '2000'))  # ms
    ticker_speed = int(os.getenv('TICKER_SPEED', '200'))  # ms
    services_limit = int(os.getenv('SERVICES_LIMIT', '10'))  # Number of services
    
    # Load configurable font sizes and colors
    title_font_size = int(os.getenv('TITLE_FONT_SIZE', '24'))
    body_font_size = int(os.getenv('BODY_FONT_SIZE', '14'))
    heading_font_size = int(os.getenv('HEADING_FONT_SIZE', '14'))
    title_color = os.getenv('TITLE_COLOR', 'orange')
    clock_color = os.getenv('CLOCK_COLOR', 'orange')
    text_color = os.getenv('TEXT_COLOR', 'orange')
    background_color = os.getenv('BACKGROUND_COLOR', 'black')
    selection_color = os.getenv('SELECTION_COLOR', 'orange')
    
    if not API_KEY:
        API_KEY = input("Enter your NRE API key: ").strip()
        if not API_KEY:
            print("No API key provided. Exiting.")
            exit(1)
    
    app = CreweDeparturesGUI(API_KEY, time_width, dest_width, plat_width, status_width, stops_width, ticker_start_delay, ticker_speed, services_limit)
    app.start()