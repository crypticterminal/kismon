#!/usr/bin/env python
"""
Copyright (c) 2010, Patrick Salecker
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice,
      this list of conditions and the following disclaimer in
      the documentation and/or other materials provided with the distribution.
    * Neither the name of the author nor the names of its
      contributors may be used to endorse or promote products derived
      from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""
import gtk
import gobject
import osmgpsmap

import os
import hashlib

class Map:
	def __init__(self, config):
		self.config = config
		self.generator_is_running = False
		self.toggle_moving_button = None
		self.markers = {}
		self.networks_label_count = 0
		self.coordinates = {}
		
		self.osm = osmgpsmap.GpsMap()
		self.osd = osmgpsmap.GpsMapOsd(show_zoom=True, show_coordinates=False, show_scale=False, show_dpad=True, show_gps_in_dpad=True)
		self.osm.layer_add(self.osd)
		self.osm.connect('button-press-event', self.on_map_pressed)
		self.widget = self.osm
		
		if os.path.isdir("/usr/share/kismon"):
			self.share_folder = "/usr/share/kismon/"
		else:
			dir = os.path.realpath(__file__).rsplit("/", 2)[0]
			self.share_folder = "%s%sfiles%s" % (dir, os.sep, os.sep)
		self.images = {
			"position": "%sposition.png" % self.share_folder
			}
		self.textures = {}
		self.create_dots()
		self.apply_config()
		
	def apply_config(self):
		pass
		
	def create_dots(self):
		for color in ("red", "orange", "green"):
			size = 16
			
			drawable = gtk.gdk.Pixmap(None, size, size, 24)
			ctx = drawable.cairo_create()
			ctx.set_source_rgba(1, 1, 1, 1)
			ctx.rectangle(0, 0, size, size)
			ctx.fill()
			ctx.stroke()
			
			if color == "red":
				ctx.set_source_rgb(1, 0, 0)
			elif color == "orange":
				ctx.set_source_rgb(1, 1, 0)
			else:
				ctx.set_source_rgb(0, 1, 0)
			
			ctx.arc(size/2, size/2, size/2-1, 0, 3.14*2)
			ctx.fill()
			ctx.stroke()
			cmap = gtk.gdk.colormap_get_system()
			pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, size, size)
			
			pixbuf.get_from_drawable(drawable, cmap, 0, 0, 0, 0, size, size)
			
			self.textures[color] = pixbuf.add_alpha(True , 255, 255, 255)
		
	def set_zoom(self, zoom):
		self.osm.set_zoom(zoom)
		
	def zoom_in(self, actor=None, event=None, view=None):
		self.osm.zoom_in()
		
	def zoom_out(self, actor=None, event=None, view=None):
		self.osm.zoom_out()
		
	def set_position(self, lat, lon, force=False):
		self.osm.gps_clear()
		self.osm.gps_add(lat, lon, heading=osmgpsmap.INVALID);
		
		self.config["last_position"] = "%s/%s" % (lat, lon)
		
	def add_marker(self, key, color, lat, lon):
		"""add a new marker to the marker_layer
		
		key: a unique key
		color: a color from self.colors
		lat: latitude
		lon: longitude
		"""
		if lat == 0.0 and lon == 0.0:
			return
		try:
			marker = self.markers[key]
			self.update_marker(marker, key, lat, lon)
			return
		except KeyError:
			pass
		
		if not self.check_position(lat, lon):
			marker = self.osm.image_add(lat, lon, self.textures[color])
		else:
			marker = DummyMarker()
		marker.color_name = color
		marker.key = key
		marker.lat = lat
		marker.lon = lon
		self.markers[key] = marker
		self.occupy_position(lat, lon, key)
		
	def update_marker(self, marker, key, lat, lon):
		if self.config["update_marker_positions"] is False:
			return
		old_lat = marker.lat
		old_lon = marker.lon
		if old_lat != lat or old_lon != lon:
			new_point = osmgpsmap.point_new_degrees(lat, lon)
			marker.set_property("point", new_point)
			
			try:
				if key in self.coordinates[old_lon][old_lon]:
					self.coordinates[old_lon][old_lon].remove(key)
			except KeyError:
				pass
			
			self.occupy_position(lat, lon, key)
			
	def occupy_position(self, lat, lon, key):
		try:
			self.coordinates[lat][lon] = [key, ]
		except KeyError:
			self.coordinates[lat] = {lon: [key, ]}
		
	def check_position(self, lat, lon):
		try:
			return self.coordinates[lat][lon]
		except KeyError:
			return False
		
	def remove_marker(self, key):
		try:
			marker = self.markers[key]
		except KeyError:
			return
		
		if not marker.get_property("point"):
			pass
		else:
			self.osm.image_remove(marker)
		del self.markers[key]
		
		try:
			if key in self.coordinates[marker.lat][marker.lon]:
				self.coordinates[marker.lat][marker.lon].remove(key)
		except KeyError:
			pass
		
	def stop_moving(self):
		self.osm.set_property("auto-center", False)
		print "stop"
	
	def start_moving(self):
		self.osm.set_property("auto-center", True)
		print "auto-center"
		
		lat, lon = self.config["last_position"].split("/")
		self.set_position(float(lat), float(lon))
		
	def on_map_pressed(self, actor, event):
		if event != None:
			if event.x >= 32 and event.x < 48 and event.y >= 32 and event.y < 48:
				self.start_moving()
		
	def locate_marker(self, key):
		if key not in self.markers:
			print "marker %s not found" % key
			return
			
		marker = self.markers[key]
		self.osm.set_center(marker.lat, marker.lon)
		
	def set_source(self, id):
		if id == "openstreetmap-renderer":
			self.osm.set_property("map-source", osmgpsmap.SOURCE_OPENSTREETMAP_RENDERER)
		else:
			id = "openstreetmap"
			self.osm.set_property("map-source", osmgpsmap.SOURCE_OPENSTREETMAP)
			
		self.config["source"] = id
		
class DummyMarker():
	def get_property(self, key):
		return False
		
	def set_property(self, key, value):
		return False

if __name__ == "__main__":
	import test
	test.map()
	gtk.main()
