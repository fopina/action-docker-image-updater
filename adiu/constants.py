MAX_PR_BODY_LENGTH = 60_000
MAX_RELEASE_NOTE_LINES_PER_IMAGE = 10
REGISTRY_TIMESTAMP_FIELDS = [
    'tag_last_pushed',  # Docker Hub tag schema: https://docs.docker.com/reference/api/hub/latest/schemas/tag/
    'imagePushedAt',  # Amazon ECR DescribeImages: https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_DescribeImages.html
    'created_at',  # GitHub Packages version schema: https://docs.github.com/en/rest/packages/packages
    'updated_at',  # GitHub Packages version schema: https://docs.github.com/en/rest/packages/packages
    'last_updated',  # Docker Hub tag schema: https://docs.docker.com/reference/api/hub/latest/schemas/tag/
    'start_ts',  # Quay tag API response: https://github.com/quay/quay/discussions/1807
    'last_modified',  # Quay tag API response: https://github.com/quay/quay/discussions/1807
    'created',  # OCI image config: https://github.com/opencontainers/image-spec/blob/main/config.md
]
