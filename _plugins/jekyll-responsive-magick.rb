##
## A Jekyll plugin for responsive images with ImageMagick.
##
##    https://indii.org/software/jekyll-responsive-magick/
##
## Copyright 2022 Lawrence Murray.
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##    http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
require 'fileutils'
require 'shellwords'

module Jekyll
  module ResponsiveMagickFilter
    @@sizes = {}

    def identify(input)
      site = @context.registers[:site]
      verbose = site.config['responsive']['verbose'] || false
      cmd = "identify -ping -format '%w,%h' .#{input.shellescape}"
      if verbose
        print("#{cmd}\n")
      end
      sizes = `#{cmd}`
      if not $?.success?
        throw "width/height: failed to execute 'identify', is ImageMagick installed?"
      end
      @@sizes[input] = sizes.split(',', 2).map!(&:to_i)
    end

    def check_path(input, filter_name)
      if not input.is_a? String || input.length == 0 || input.chr != '/'
        throw "#{filter_name}: path must be an absolute path"
      end
    end

    def is_image?(src)
      cmd = "identify -ping #{src.shellescape} 2>&1"
      output = `#{cmd}`

      if not $?.success?
        if output.include?("identify: improper image header")
          throw "file is not an image: '#{src}'"
        else
          throw "width/height: failed to execute 'identify', is ImageMagick installed?"
        end
      end

      return true
    end

    def srcset(input)
      check_path(input, "srcset")
      site = @context.registers[:site]
      dirname = File.dirname(input).gsub('assets/img', '/assets/thumbs')
      basename = File.basename(input, '.*')
      extname = File.extname(input)
      new_extname = site.config['responsive']['format'] ? ".#{site.config['responsive']['format']}" : extname
      src = ".#{dirname}/#{basename}#{extname}"
      srcwidth = width(input, "srcset")      
      srcset = ["#{input} #{srcwidth}w"]

      # if not File.exist?(src) or not is_image?(src)
      #  throw "srcset: file does not exist or is not an image: '#{src}'"
      if File.extname(src) != '.svg'
        widths = site.config['responsive']['widths'] || [576, 768, 992, 1200, 1400]
        
        widths.each do |width|
          if srcwidth > width
            file = "#{basename}-#{width}w#{new_extname}"
            srcset.push("#{dirname}/#{file} #{width}w")
          end
        end
      end

      return srcset.join(', ')
    end

    def width(input, from = "width")
      check_size(input, from)
      return @@sizes[input][0]
    end

    def height(input, from = "height")
      check_size(input, from)
      return @@sizes[input][1]
    end

    def check_size(input, from)
      check_path(input, from)
      if not @@sizes[input]
        identify(input)
      end
    end
  end
end

Liquid::Template.register_filter(Jekyll::ResponsiveMagickFilter)#