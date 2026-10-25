FROM apify/actor-node:24
COPY package.json ./
RUN npm install --omit=dev --omit=optional
COPY . ./
CMD npm start --silent
