data "aws_ami" "amazon_linux" {
  most_recent = true

  filter {
    name   = "name"
    values = ["amzn2-ami-kernel-5.10-hvm-2.0.*-x86_64-gp2"]
  }
  owners = ["amazon"]
}

resource "aws_iam_role" "bot" {
  name               = "${local.prefix}-bot"
  assume_role_policy = file("./templates/bot/instance-profile-policy.json")

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "bot_attach_policy" {
  role       = aws_iam_role.bot.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "bot" {
  name = "${local.prefix}-bot-instance-profile"
  role = aws_iam_role.bot.name
}

resource "aws_instance" "bot" {
  ami                  = data.aws_ami.amazon_linux.id
  instance_type        = "t2.micro"
  user_data            = file("./templates/bot/user-data.sh")
  iam_instance_profile = aws_iam_instance_profile.bot.name
  key_name             = var.bot_key_name
  subnet_id            = aws_subnet.public_a.id

  vpc_security_group_ids = [
    aws_security_group.bot.id
  ]


  tags = merge(
    local.common_tags,
    tomap(
      {
        "Name" = "${local.prefix}-bot"
      })
  )
}

resource "aws_security_group" "bot" {
  description = "Control bot inbound and outbound access"
  name        = "${local.prefix}-bot"
  vpc_id      = aws_vpc.main.id

  ingress {
    protocol    = "tcp"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    protocol    = "tcp"
    from_port   = 80
    to_port     = 80
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    protocol  = "tcp"
    from_port = 5432
    to_port   = 5432
    cidr_blocks = [
      aws_subnet.private_a.cidr_block,
      aws_subnet.private_b.cidr_block,
    ]
  }

  tags = local.common_tags
}