package com.ssafy.edith.scg.config;

import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class GatewayConfig {

    @Bean
    public RouteLocator websocketRoutes(RouteLocatorBuilder builder) {
        return builder.routes()
                .route("websocket_route", r -> r.path("/ws/v1/face-recognition/face-login")
                        .uri("ws://face-recognition-fastapi-service:8184"))
                .build();
    }
}