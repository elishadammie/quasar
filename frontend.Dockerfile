# frontend.Dockerfile

# Use the official Nginx image from Docker Hub
FROM nginx:stable-alpine

# Remove the default Nginx configuration file
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom Nginx configuration file
COPY nginx.conf /etc/nginx/conf.d/

# Copy the static frontend files (HTML, CSS, JS)
COPY ./frontend /usr/share/nginx/html