package com.ssafy.edith.user.api.controller;

import com.ssafy.edith.user.api.request.EmbeddingRequest;
import com.ssafy.edith.user.api.request.FaceLoginRequest;
import com.ssafy.edith.user.api.request.SignInRequest;
import com.ssafy.edith.user.api.request.SignUpRequest;
import com.ssafy.edith.user.api.response.SignInResponse;
import com.ssafy.edith.user.api.response.UserInfoResponse;
import com.ssafy.edith.user.api.service.UserService;
import com.ssafy.edith.user.util.CookieUtil;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import static com.ssafy.edith.user.api.controller.ApiUtils.success;
import static com.ssafy.edith.user.api.controller.ApiUtils.ApiResult;

@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
@Slf4j
public class UserController {
    private final UserService userService;
    private final CookieUtil cookieUtil;

    @GetMapping("/validate")
    @ResponseStatus(HttpStatus.OK)
    public ApiResult<Void> validateToken() {
        return success(null);
    }

    @PostMapping("/sign-up")
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResult<Void> signUp(@RequestBody SignUpRequest signUpRequest) {
        userService.signUp(signUpRequest);
        return success(null);
    }
    @PostMapping("/logout")
    @ResponseStatus(HttpStatus.OK)
    public ApiResult<Void> logout(HttpServletResponse response) {
        cookieUtil.removeAccessToken(response);
        cookieUtil.removeRefreshToken(response);
        return success(null);
    }

    @PostMapping("/sign-in")
    @ResponseStatus(HttpStatus.OK)
    public ApiResult<SignInResponse> signIn(@RequestBody SignInRequest signInRequest, HttpServletResponse response) {
        SignInResponse signInResponse = userService.signIn(signInRequest);

        cookieUtil.addAccessToken(response, signInResponse.accessToken());
        cookieUtil.addRefreshToken(response, signInResponse.refreshToken());

        return success(signInResponse);
    }
    @PostMapping("/face-login")
    @ResponseStatus(HttpStatus.OK)
    public ApiResult<SignInResponse> faceLogin(@RequestBody FaceLoginRequest faceLoginRequest, HttpServletResponse response) {
        SignInResponse signInResponse = userService.faceLogin(faceLoginRequest.userId());

        cookieUtil.addAccessToken(response, signInResponse.accessToken());
        cookieUtil.addRefreshToken(response, signInResponse.refreshToken());

        return success(signInResponse);
    }
    @PostMapping("/token/refresh")
    @ResponseStatus(HttpStatus.OK)
    public ApiResult<String> refreshToken(@CookieValue("refreshToken") String refreshToken) {
        String newAccessToken = userService.refreshAccessToken(refreshToken);
        return success(newAccessToken);
    }
    @PostMapping("/face/register")
    @ResponseStatus(HttpStatus.OK)
    public ApiResult<Void> registerFaceEmbedding(@RequestBody EmbeddingRequest embeddingRequest,
                                                   @CookieValue("accessToken") String accessToken) {
        log.info("Embedding vector length: {}", embeddingRequest.embeddingVectors().length);
        userService.registerFaceEmbedding(embeddingRequest,accessToken);
        return success(null);
    }

    @GetMapping("/info")
    public ApiResult<UserInfoResponse> getUserInfo(@CookieValue("accessToken") String accessToken) {
        log.info("User 서버에서 받은Received JWT Token: {}", accessToken);
        UserInfoResponse userInfoResponse = userService.getUserInfo(accessToken);
        return success(userInfoResponse);
    }

    @GetMapping()
    public ApiResult<UserInfoResponse> getUserById(@CookieValue("accessToken") String accessToken) {

        UserInfoResponse userInfoResponse = userService.getUserInfo(accessToken);
        return success(userInfoResponse);
    }
}
